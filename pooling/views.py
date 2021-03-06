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
    # List active batches
    batches = Batch.objects.filter(finished__isnull=True)
    # Now the active batch
    batchid = request.session.get('pooling_batch',False)
    if batchid:
        batch = get_object_or_404(Batch,identifier=batchid)
    # Sample racks
    freeracks = Rack.objects.filter(position=0,pool=False,finished=False)
    poolracks = Rack.objects.filter(position=0,pool=True,finished=False)
    # The rack list
    racks = {}
    # Are we working on a robot or loading
    robot = None
    robotid = request.session.get('pooling_robot',False)
    if robotid:
        robot = Robot.objects.filter(identifier=robotid)
    # No refresh until the pooling process starts on a connected robot
    refresh = False
    if request.session.get('pooling_atwork',False):
        refresh = settings.POOLING_REFRESH

    # We display racks on their corresponding trays
    for tray in [2]+ordering:
        r = Rack.objects.filter(position=tray,robot=robot)
    #    if not r:
    #   else:
        if r:
            racks[tray] = r[0]
        else:
            racks[tray] = None
            
    # If there is no current rack,
    # or the one in the session is not anymore in the robot
    # we start with the first one, insertion will take care of filling control
    current = request.session.get('pooling_rack',False)
    if current not in [racks[r].id for r in racks if racks[r]]:
        if racks[ordering[0]]:
            request.session['pooling_rack'] = racks[ordering[0]].id

    return render(request,'pooling/index.html',{'refresh': refresh,
                                                'batches': batches,
                                                'freeracks': freeracks,
                                                'poolracks': poolracks,
                                                'batch': batch,
                                                'rackf': racks[2],
                                                'rack1': racks[1],
                                                'rack3': racks[3],
                                                'rack4': racks[4],
                                                'rack6': racks[6]})


def newRack(request,tray):
    """
    Creates a new empty rack for a given tray
    """
    rack = Rack()
    rack.racktype = 1
    rack.position = tray
    if int(tray) == 2:
        # Mark as a pooling rack
        rack.pool = True
    # If the rack is created from the robot view, indicate so
    robotid = request.session.get('pooling_robot',False)
    if robotid:
        robot = Robot.objects.filter(identifier=robotid)
        rack.robot = robot[0]
    rack.save()
    return HttpResponseRedirect(reverse('pooling:inicio'))


def loadRack(request,tray):
    """
    Loads a rack onto a tray, on the current robot if there is one
    """
    if request.method == "POST":
       rackid = request.POST.get('rack',None)
    if rackid:
        rack = get_object_or_404(Rack,pk=rackid)
    robotid = request.session.get('pooling_robot',False)
    if robotid:
        robot = Robot.objects.filter(identifier=robotid)
        rack.robot = robot[0]
    rack.position = tray
    rack.save()
    return HttpResponseRedirect(reverse('pooling:inicio'))


def batch(request):
    """
    Selects the batch to draw samples from
    """

    if request.method == "GET":
       batchid = request.GET.get('batchid',None)
    if request.method == "POST":
       batchid = request.POST.get('batchid',None)
    if batchid:
        batch = get_object_or_404(Batch,pk=batchid)
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
    return render(request,'pooling/history.html',
                  {'racks': racks, 'date': date})


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
    # They MUST (RFC 2119) be directly connected to the server
    remoteip = request.META.get('REMOTE_ADDR')
    robot = get_object_or_404(Robot,ip=remoteip)
    data = json.loads(request.body)
    # Get source rack
    rackO = get_object_or_404(Rack,robot=robot,
                                   position=data['source']['tray'])
    # Get origin tube
    tubeO = get_object_or_404(Tube,rack=rackO,
                                   row=data['source']['row'],
                                   col=data['source']['col'])
    # Find the moving sample
    sample = get_object_or_404(Sample,tube=tubeO)

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
    

def start(request):
    """
    Starts refreshing the robot display, waiting for movements
    """
    # Somo consistency checks
    robot = get_object_or_404(Robot,
                              identifier=request.session.get('pooling_robot',''))
    rack = Rack.objects.filter(robot=robot,position=2)
    if len(rack) == 0:
        messages.error(request,_('There is no rack on tray 2'))
        return HttpResponseRedirect(reverse('pooling:inicio'))
    rack = rack[0]
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
    request.session['pooling_atwork'] = True
    return HttpResponseRedirect(reverse('pooling:inicio'))


def stop(request):
    """
    Stops refreshing the robot display and waiting for movements
    """
    # Safewarding, just in case
    if request.session.get('pooling_atwork',False):
        del (request.session['pooling_atwork'])
    return HttpResponseRedirect(reverse('pooling:inicio'))


def togle(request):
    """
    Changes the view from robot display to rack loading and back
    """
    robot = request.session.get('pooling_robot',False)
    if robot:
        del request.session['pooling_robot']
    else:
        robot = Robot.objects.first()
        request.session['pooling_robot'] = robot.identifier

    return HttpResponseRedirect(reverse('pooling:inicio'))


def refresh(request):
    """
    Updates the display showing movements sent from the robot.
    """
    # Find the robot we are presenting
    robotid = request.session.get('pooling_robot','')
    robot = get_object_or_404(Robot, identifier=robotid)
    # Get the racks in the robot and fill the grid
    data = []
    # Ready for detecting the end of the process
    racks = Rack.objects.filter(robot=robot)
    count = len(racks)
    for rack in racks:
        if rack.isEmpty(): count -= 1
        for g in rack.grid(): 
            cell = {}
            cell['cell'] = 'R{0}{1}{2}'.format(rack.position,g['row'],g['col'])
            cell['samples'] = g['samples']
            data.append(cell)
    # If there is only one non-empty rack, the operation has finished
    if count == 1:
        if request.session.get('pooling_atwork',False):
            del request.session['pooling_atwork']
        data = 'reload'
    return JsonResponse({'data': data})


def move(request):
    """
    Simulates pooling by moving all samples into the pooling rack
    """

    request.session['pooling_simulating'] = True
    rack = get_object_or_404(Rack,robot=None,position=2)
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
    robot = request.session.get('pooling_robot',False)
    if not robot:
        rack = get_object_or_404(Rack,position=2)
    else:
        rack = get_object_or_404(Rack,robot__identifier=robot,position=2)
    # If we are on a robot or simulating, check if the poolling has been done
    if (request.session.get('pooling_robot',False) or
        request.session.get('pooling_simulating',False)):
        if rack.position == 2 and rack.isEmpty():
            messages.error(request,
                    _('Samples have not been pooled into {0}').format(rack))
            return HttpResponseRedirect(reverse('pooling:inicio'))
        
    # Remove racks
    for tray in ordering:
        if not robot:
            r = Rack.objects.filter(position=tray)
        else:
            r = Rack.objects.filter(robot__identifier=robot,position=tray)
        if len(r) == 1:
            if (request.session.get('pooling_robot',False) or
                request.session.get('pooling_simulating',False)):
                if not r[0].isEmpty():
                    messages.error(request,
                                   _('Rack {0} is nor empty').format(rack))
                    return HttpResponseRedirect(reverse('pooling:inicio'))
            r[0].position = 0
            r[0].robot = None
            r[0].save()

    # And the pooling rack leaves the robot as well
    rack.position = 0
    rack.robot = None
    # We mark rack as finished if removing from robot or simulating
    if (request.session.get('pooling_robot',False) or
        request.session.get('pooling_simulating',False)): rack.finished = True
    rack.save()
    # No current rack for the session anymore
    del request.session['pooling_rack']
    # If we were simulating, simulation has finished
    if request.session.get('pooling_simulating',False):
        del request.session['pooling_simulating']
    messages.success(request,_('{0} removed. Pooling finished.').format(rack))

    return HttpResponseRedirect(reverse('pooling:inicio'))


def loadTube(request):
    """
    Inserts a tube in the next free slot in the current rack.
    The algorithm works in row first mode, i.e.: A1,A2,A3,...,H10,H11,H12
    """

    racks = Rack.objects.filter(position=2)
    if not len(racks) == 1:
        response = JsonResponse({"error": _("Wrong Rack for tray 2")})
        response.status_code = 404
        return response
    # We have a single rack as expected
    rack = racks[0]
    if rack.isFull():
        return JsonResponse({"error": _("The pooling rack is full")},
                            status = 404)
    if request.method == 'POST':
       identifier = request.POST.get('tubeid',None)
    if not identifier:
        return JsonResponse({"error": _("No Tube Identifier")},
                            status = 404)
    tube = Tube.objects.filter(identifier=identifier)
    if tube:
        return JsonResponse({"error":
                             _("Tube {0} Added Already").format(identifier)},
                            status = 404)

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

    rackid = request.session.get('pooling_rack', 0)
    racks = Rack.objects.filter(id=rackid)
    if not len(racks) == 1:
        return JsonResponse({"error":
                             _("Wrong Rack Identifier {0}").format(rackid)},
                            status = 404)
    # We have a single rack as expected
    rack = racks[0]
    full = rack.isFull()
    if full and rack.position == ordering[-1]:
        return JsonResponse({"error": _("All racks are full")},
                            status = 404)
    if full:
        # Let's start filling the next rack
        nextrack = ordering[ordering.index(rack.position)+1]
        rack = get_object_or_404(Rack,position=nextrack)
        request.session['pooling_rack'] = rack.id
    batchid = request.session.get('pooling_batch',0)
    if request.method == 'POST':
       identifier = request.POST.get('identifier',None)
    if not identifier:
        return JsonResponse({"error": _("No Sample Identifier")},
                            status = 404)
    # If we are working with a "pre-loaded" batch
    batch = get_object_or_404(Batch,identifier=batchid)
    sample = Sample.objects.filter(batch=batch,code=identifier)
    if batch.preloaded and not len(sample) == 1:
        return JsonResponse({"error":
                             _("Wrong Sample Code {0}:{1}").format(batchid,
                                                                  identifier)},
                            status = 404)
    if len(sample) and sample[0].tube:
        return JsonResponse({"error":
                             _("Sample {0} Added Already").format(identifier)},
                             status = 404)
    # If we do not have a sample yet, we do not have a pre-loaded batch
    if not batch.preloaded and len(sample) == 0:
        sample = [Sample()]
        sample[0].code = identifier
        sample[0].batch = batch
        sample[0].save()

    # Place the sample in the next available tube
    rack.insertSample(sample[0])
    tube = sample[0].tube
    # If it is the first sample from a batch, we mark the start of processing
    if not sample[0].batch.started:
        sample[0].batch.started = datetime.datetime.now()
        sample[0].batch.save()

    return JsonResponse({'row': tube.row, 'col': tube.col,
                         'pos': rack.position, 'samples': sample[0].code })


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
    # If we do not have a file, it's a "pre-loaded" batch
    if len(request.FILES):
        samples = request.FILES['samples']
        import csv,io
        samples.seek(0)
        lines = csv.DictReader(io.StringIO(samples.read().decode('utf-8')))
        for line in lines:
            sample = Sample()
            sample.batch = batch
            sample.code = line['code']
            sample.save()
    else:
        batch.preloaded = False
        batch.save()
    text = _('Batch {0} with {1} samples uploaded successfully')
    messages.success(request,
                     text.format(batch.identifier,
                                 len(batch.sample_set.all())))
    return HttpResponseRedirect(reverse('pooling:inicio'))

