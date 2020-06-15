# -*- coding: utf-8 -*-
# vim:ts=4:expandtab:ai
# $Id: $
from django.shortcuts import render,get_object_or_404
from django.http import HttpResponseRedirect,JsonResponse,HttpResponse
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib import messages
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

from .models import *
from .forms import loadBatch

import datetime, json

# Rack position ordering
ordering = [1,3,4,6]

# Create your views here.

def index(request):
    """
    Initial view to represent the robot grid with racks for pooling
    """

    batch = Batch()
    robot = False
    # List active batches
    batches = Batch.objects.filter(finished__isnull=True)
    # List idle robots
    robots = [r for r in Robot.objects.all() if len(r.rack_set.all()) == 0]
    # Now the active robot and batch
    robotid = request.session.get('pooling_robot',False)
    batchid = request.session.get('pooling_batch',False)
    if robotid:
        robot = get_object_or_404(Robot,identifier=robotid)
        # We add the current robot to the front of list
        robots.insert(0,robot)
    if batchid:
        batch = get_object_or_404(Batch,identifier=batchid)
    # The rack list
    racks = {}
    # No refresh until the pooling process starts on a connected robot
    refresh = False

    # If there are no free racks, we create and place them
    # but only now that we know the robot we are working with
    for tray in [2]+ordering:
        r = Rack.objects.filter(position=tray)
        if robot: r.filter(robot=robot)
        if not r:
            racks[tray] = Rack()
            racks[tray].racktype = 1
            if robot: racks[tray].robot = robot
            racks[tray].position = tray
            racks[tray].save()
        else:
            racks[tray] = r[0]
        # If sample rack has no tubes, we create them
        if ( not racks[tray].position == 2 and
             len(racks[tray].tube_set.all()) == 0 ):
            for col in racks[tray].listCols():
                for row in racks[tray].listRows():
                    tube = Tube()
                    tube.rack = racks[tray]
                    tube.row = row
                    tube.col = col[0]
                    tube.save()
            
    # If there is no current rack,
    # or the one in the session is not anymore in the robot
    # we start with the first one, insertion will take care of filling control
    current = request.session.get('pooling_rack',False)
    if current not in [racks[r].id for r in racks ]:
        request.session['pooling_rack'] = racks[ordering[0]].id

    if robot.connected:
        refresh = settings.POOLING_REFRESH
    return render(request,'pooling/index.html',{'refresh': refresh,
                                                'batches': batches,
                                                'robots': robots,
                                                'robot': robot,
                                                'batch': batch,
                                                'rackf': racks[2],
                                                'rack1': racks[ordering[0]],
                                                'rack2': racks[ordering[1]],
                                                'rack3': racks[ordering[2]],
                                                'rack4': racks[ordering[3]]})


def batch(request):
    """
    Selects the batch to draw samples from and the robot to place the racks on
    """

    if request.method == "GET":
       robotid = request.GET.get('robotid',None)
       batchid = request.GET.get('batchid',None)
    if request.method == "POST":
       robotid = request.POST.get('robotid',None)
       batchid = request.POST.get('batchid',None)
    if robotid:
        robot = get_object_or_404(Robot,pk=robotid)
    if batchid:
        batch = get_object_or_404(Batch,pk=batchid)
    request.session['pooling_robot'] = robot.identifier
    request.session['pooling_batch'] = batch.identifier
    request.session['pooling_poolsize'] = batch.poolsize
    return HttpResponseRedirect(reverse('pooling:inicio'))


def history(request):
    """
    Presents finished pools, by default the last ones.
    """

    lastdate = Rack.objects.filter(finished=True).first().modifiedOn.date()
    if request.method == 'GET':
       date = lastdate
    if request.method == 'POST':
        date = request.POST.get('date',lastdate)

    racks = Rack.objects.filter(finished=True,modifiedOn__date=date)
    if racks: date = racks.first().modifiedOn.date()
    return render(request,'pooling/history.html',{'racks': racks, 'date': date})


@csrf_exempt
def moveSample(request):
    """
    Moves a sample as instructed by the robot where it is really hapening.
    The movement data arrives as a JSON object in the request body like:
    {'source': {'tray': 1, 'row': 'A', 'col': 1}, 
     'destination': {'tray': 2, 'row': 'A', 'col': 1}}
    """

    # We are expecting a POST request, any other type is an error
    if not request.method == 'POST':
       return HttpResponse("Bad method",status=400,content_type="text/plain") 
    # We first verify that the request comes from one of our robots
    robot = get_object_or_404(Robot,ip=request.remoteip)
    data = json.loads(request.body)
    # Get source rack
    rackO = get_object_or_404(Rack,robot=robot,
                                   position=data['source']['tray'])
    # Get origin tube
    tubeO = get_object_or_404(Tube,rack=rackO,
                                   row=data['source']['row'],
                                   col=data['source']['col'])
    # Find the moving sample
    sample = get_object_or_404(Sample,tube=tube)

    # Get destination rack
    rackD = get_object_or_404(Rack,robot=robot,
                                   position=data['destination']['tray'])
    # Get the destination tube
    tubeD = get_object_or_404(Tube,rack=rackD,
                                   row=data['destination']['row'],
                                   col=data['destination']['col'])
    # Move the sample
    sample.tube = tubeD
    sample.save()

    return HttpResponse("OK",status=200,content_type="text/plain") 
    

def refresh(request):
    """
    Updates the display showing movements sent from the robot.
    """
    # Find the robot we are presenting
    robot = get_object_or_404(Robot,
                              identifier=session.get('pooling_robot',''))
    # Get the racks in the robot and fill the grid
    data = {}
    for rack in Rack.objects.filter(robot=robot):
        for g in rack.grid(): 
            data['cell'] = 'R{0}{1}{2}'.format(rack.tray,g['row'],g['col'])
            data['samples'] = g['samples']
    return JsonResponse({'data': data})


def move(request):
    """
    Moves all samples into the pooling rack
    """

    rack = get_object_or_404(Rack,position=2)
    poolsize = request.session.get('pooling_poolsize',
                                   settings.POOL_TUBE_SAMPLES)
    # Deepwells leave station with all samples in them if there is any
    if rack.isFull(poolsize):
        messages.error(request,_('{0} is full').format(rack))
        return HttpResponseRedirect(reverse('pooling:inicio'))
    if len(rack.tube_set.all()) == 0:
        messages.error(request,
                _('There are no tubes in {0} for the pools').format(rack))
        return HttpResponseRedirect(reverse('pooling:inicio'))
    samples = 0
    racks = Rack.objects.filter(position__in=ordering)
    for r in racks:
        samples += r.numSamples()
    if (rack.numTubes()*poolsize - rack.numSamples()) < samples:
        messages.error(request,
                _('There are not enough free tubes in {0}').format(rack))
        return HttpResponseRedirect(reverse('pooling:inicio'))
    for tray in ordering:
        r = [x for x in racks if x.position == tray]
        if len(r) == 1:
            for tube in r[0].tube_set.all().order_by('row','col'):
                if tube.isEmpty(): continue
                if rack.isFull(): break
                sample = tube.sample_set.all().first()
                rack.insertSample(sample,pool=True)
                sample.finished = True
                sample.save()
    messages.success(request,_('{0} filled').format(rack))

    return HttpResponseRedirect(reverse('pooling:inicio'))


def finish(request):
    """
    Finishes the run and moves all racks out of the pooling robot
    """
    rack = get_object_or_404(Rack,position=2)
    # Check if the poolling has been done
    if rack.position == 2 and rack.isEmpty():
        messages.error(request,_('Samples have not been pooled into {0}').format(rack))
        return HttpResponseRedirect(reverse('pooling:inicio'))
        
    # Remove racks if they are empty
    for tray in ordering:
        r = Rack.objects.filter(position=tray)
        if len(r) == 1:
            if r[0].isEmpty():
                r[0].position = 0
                r[0].save()
            else:
                messages.error(request,_('Rack {0} is nor empty').format(rack))
                return HttpResponseRedirect(reverse('pooling:inicio'))

    # And the pooling racks leaves the robot as well
    rack.position = 0
    rack.finished = True
    rack.save()
    # No current rack for the session anymore
    del request.session['pooling_rack']
    messages.success(request,_('{0} removed. Pooling finished.').format(rack))

    return HttpResponseRedirect(reverse('pooling:inicio'))


def loadTube(request):
    """
    Inserts a tube in the next free slot in the current rack.
    The algorithm works in row first mode, i.e.: A1,A2,A3,...,H10,H11,H12
    """

    racks = Rack.objects.filter(position=2)
    if not len(racks) == 1:
        response = JsonResponse({"error": _("Wrong Rack Identifier {0}").format(rackid)})
        response.status_code = 404
        return response
    # We have a single rack as expected
    rack = racks[0]
    if rack.isFull() and rack.position == ordering[-1]:
        response = JsonResponse({"error": _("All racks are full")})
        response.status_code = 404
        return response
    if rack.isFull():
        response = JsonResponse({"error": _("The pooling rack is full")})
        response.status_code = 404
    if request.method == 'POST':
       identifier = request.POST.get('tubeid',None)
    if not identifier:
        response = JsonResponse({"error": _("No Tube Identifier")})
        response.status_code = 404
        return response
    tube = Tube.objects.filter(identifier=identifier)
    if tube:
        response = JsonResponse({"error": _("Tube {0} Added Already").format(identifier)})
        response.status_code = 404
        return response

    tube = Tube()
    tube.identifier = identifier
    # Place the tube in the next available position
    rack.insertTube(tube)

    return JsonResponse({'row': tube.row, 'col': tube.col,
                         'samples': tube.numSamples()})


def loadSample(request):
    """
    Inserts a sample in the next free well in the current rack.
    The algorithm works in row first mode, i.e.: A1,A2,A3,...,H10,H11,H12
    """

    # We are working on a given robot
    robotid = request.session.get('pooling_robot',False)
    robot = get_object_or_404(Robot,identifier=robotid)
    rackid = request.session.get('pooling_rack', 0)
    racks = Rack.objects.filter(id=rackid)
    if not len(racks) == 1:
        response = JsonResponse({"error": _("Wrong Rack Identifier {0}").format(rackid)})
        response.status_code = 404
        return response
    # We have a single rack as expected
    rack = racks[0]
    full = rack.isFull()
    if full and rack.position == ordering[-1]:
        response = JsonResponse({"error": _("All racks are full")})
        response.status_code = 404
        return response
    if full:
        # Let's start filling the next rack
        nextrack = ordering[ordering.index(rack.position)+1]
        rack = get_object_or_404(Rack,robot=robot,position=nextrack)
        request.session['pooling_rack'] = rack.id
    batchid = request.session.get('pooling_batch',0)
    if request.method == 'POST':
       identifier = request.POST.get('identifier',None)
    if not identifier:
        response = JsonResponse({"error": _("No Sampe Identifier")})
        response.status_code = 404
        return response
    sample = Sample.objects.filter(batch__identifier=batchid,code=identifier)
    if not len(sample) == 1:
        response = JsonResponse({"error":
                   _("Wrong Sample Code {0}:{1}").format(batchid,identifier)})
        response.status_code = 404
        return response
    if sample[0].tube:
        response = JsonResponse({"error": _("Sample {0} Added Already").format(identifier)})
        response.status_code = 404
        return response

    # Place the sample in the next available tube
    rack.insertSample(sample[0])
    tube = sample[0].tube
    # If it is the first sample from a batch, we mark the start of processing
    if not sample[0].batch.started:
        sample[0].batch.started = datetime.datetime.now()
        sample[0].batch.save()

    return JsonResponse({'row': tube.row, 'col': tube.col, 'pos': rack.position})


def viewtube(request,tubeid):
    """
    Show sample information
    """

    tube = get_object_or_404(Tube,id=tubeid)
    return render(request,'pooling/tube.html',{'tube': tube })


def show(request,rackid):
    """
    Presents a grid with the samples in a rack.
    """

    rack = get_object_or_404(Rack,id=rackid)
    return render(request,'pooling/rack.html',{'rack': rack})


def upload(request):
    """
    Creates a sample batch from a CSV file (only the "code" field is used)
    First row should look like (ellipsys means other discarded columns):
    ...,code,... OR ...,"code",...
    Subsequent rows shoud look like:
    ...,sample-code,...
    It also asigns the batch to a Technician.
    """

    if request.method == 'GET':
        form = loadBatch()
        return render(request,'pooling/upload.html',{'form': form})
    if not request.method == 'POST':
      messages.error(_('Wrong method'))
      return HttpResponseRedirect(reverse('pooling:inicio'))

    form = loadBatch(request.POST, request.FILES)
    if not form.is_valid():
        return render(request,'pooling/upload.html',{'form': form})

    batch = Batch()
    if form.cleaned_data['batchid']:
        batch.identifier = form.cleaned_data['batchid']
    batch.technician = get_object_or_404(Technician,
                                         id=form.cleaned_data['techid'])
    batch.poolsize = form.cleaned_data['poolsize']
    batch.save()
    request.session['pooling_batch'] = batch.identifier
    request.session['pooling_poolsize'] = batch.poolsize
    import csv,io
    samples = request.FILES['samples']
    samples.seek(0)
    for line in csv.DictReader(io.StringIO(samples.read().decode('utf-8'))):
        sample = Sample()
        sample.batch = batch
        sample.code = line['code']
        sample.save()
    messages.success(request,
                     _('Batch {0} with {1} samples uploaded successfully').format(
                       batch.identifier,len(batch.sample_set.all())))
    return HttpResponseRedirect(reverse('pooling:inicio'))

