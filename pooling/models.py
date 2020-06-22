# -*- coding: utf-8 -*-
# vim:ts=4:expandtab:ai
# $Id: $

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
import time,datetime,uuid

# Create your models here.
class Robot(models.Model):
    identifier = models.CharField(verbose_name=_('identifier'),
                                  max_length=32, blank=True, null=True,
                                  db_index=True, editable=True)
    ip = models.GenericIPAddressField(verbose_name=_('IP address'),
                                      max_length=255, unique=True)
    connected = models.BooleanField(verbose_name=_('Can communicate with server'),
                                    default=True,db_index=True, editable=True)

    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)


    class Meta:
        ordering = ['-modifiedOn']


    def __str__(self):
        return '{0} {1}'.format(self.ip,self.identifier)


    def save(self, *args, **kwargs):
        if not self.identifier or self.identifier.strip() == '':
            self.identifier = uuid.uuid4().hex
        super(Robot, self).save()


    def isFree(self):
        return len(self.rack_set.all()) == 0


    pass


class Technician(models.Model):
    identifier = models.CharField(verbose_name=_('identifier'),
                                  max_length=32, blank=True, null=True,
                                  db_index=True, editable=False)
    name = models.CharField(max_length=100,verbose_name=_('Name'),db_index=True)

    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)


    class Meta:
        ordering = ['name','-modifiedOn']


    def __str__(self):
        return self.name


    def save(self, *args, **kwargs):
        if not self.identifier or self.identifier.strip() == '':
            self.identifier = uuid.uuid4().hex
        super(Technician, self).save()


    pass


class Batch(models.Model):
    identifier = models.CharField(verbose_name=_('identifier'),
                                  max_length=32, blank=True, null=True,
                                  db_index=True, editable=False)
    technician = models.ForeignKey(Technician)
    poolsize = models.IntegerField(verbose_name=_('Pool size'),
                                   default=settings.POOL_TUBE_SAMPLES)
    preloaded = models.BooleanField(verbose_name=_('Pre-loaded batch'),default=True)
    started = models.DateTimeField(_('Processing started on'),
                                   db_index=True,null=True,blank=True)
    finished = models.DateTimeField(_('Processing completed on'),
                                    db_index=True,null=True,blank=True)


    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)

 
    class Meta:
        verbose_name_plural = _('Batches')
        ordering = ['identifier','technician','-modifiedOn']


    def __str__(self):
        return _('{0}: {1} samples, {2} -> {3} by {4}').format(self.identifier,
                                                               self.samples(),
                                                               self.started,
                                                               self.finished,
                                                               self.technician)


    def samples(self):
        return len(self.sample_set.all())


    def save(self, *args, **kwargs):
        if not self.identifier or self.identifier.strip() == '':
            self.identifier = uuid.uuid4().hex
        if (len(self.sample_set.filter(finished=False)) == 0 and
                not len(self.sample_set.filter(finished=True)) == 0):
            self.finished = datetime.datetime.now()
        super(Batch, self).save()


    pass


class Rack(models.Model):
    TYPE = [(1,'24'),(2,'96')]
    DEEPWELL = 1
    POSITION = [(1,'1'),(2,'2'),(3,'3'),(4,'4'),(5,'5'),(6,'6')]
    ROWCOLS = {1:('D',6),2:('H',12)} 
    identifier = models.CharField(verbose_name=_('identifier'),
                                  max_length=32, blank=True, null=True,
                                  db_index=True, editable=False)
    racktype = models.IntegerField(verbose_name=_('Rack type'),
                                   choices=TYPE,db_index=True)
    pool = models.BooleanField(verbose_name=_('Pooling rack'),
                               default=False,db_index=True)
    robot = models.ForeignKey(Robot,null=True)
    position = models.IntegerField(choices=POSITION,db_index=True,default=0)
    finished = models.BooleanField(verbose_name=_('Processing completed'),
                                   default=False,db_index=True)

    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)

 
    class Meta:
        ordering = ['-modifiedOn']


    def listCols(self):
        return [(x,'%d' % x) 
                for x in range(1,self.ROWCOLS[self.racktype][1]+1)]


    def listRows(self):
        return 'ABCDEFGH'[:'ABCDEFGH'.index(self.ROWCOLS[self.racktype][0])+1]


    def numSlots(self):
        return len(self.listCols()) * len(self.listRows())

    def isEmpty(self):
        # An empty rack has no samples :-)
        return sum([len(t.sample_set.all())
                    for t in self.tube_set.all()]) == 0


    def numSamples(self):
        return sum([len(t.sample_set.all())
                    for t in self.tube_set.all()])

    def numTubes(self):
        """
        Returns the number of tubes in a rack
        """
        return len(self.tube_set.all())


    def freeSlots(self):
        """
        Returns how many positions in the grid do not have a tube
        """
        return self.numSlots() - len(self.tube_set.all())


    def isFull(self,poolsize=settings.POOL_TUBE_SAMPLES):
        # A rack is full if the number of full tubes equals number of slots
        # We pool into position 2
        size = self.numSlots()
        if self.pool :
            size = size * poolsize
        return self.numSamples() == size


    def grid(self):
        # It is easier to organise the tubes here than on the template
        # There should be no empty places between tubes,
        # better safe that sorry
        grid = []
        for r in self.listRows():
            for c in self.listCols():
                grid.append({'row': r , 'col': c[0], 'samples': 0})
        for t in self.tube_set.all():
            g = [x for x in grid if x['col'] == t.col and x['row'] == t.row]
            if len(g) == 1:
              g[0]['tubeid'] = t.id
              g[0]['tube'] = t.identifier
              samples = len(t.sample_set.all())
              if samples > 1 or self.pool :
                identifier = t.identifier
                if len(identifier) > 5: 
                    identifier = '...{}'.format(identifier[-4:])
                g[0]['samples'] = '{0}({1})'.format(identifier,samples)
              if samples == 1:
                  g[0]['samples'] = t.sample_set.first().code
              

        return grid

   
    def insertTube(self,tube):
        """
        Places a tube in the first free position in the rack
        The algorithm works in row first mode, i.e.:
        A1,A2,A3,...,H10,H11,H12
        """
        if not self.freeSlots(): return False
        # Find the first free position
        rows = self.listRows()
        if self.numSlots() == self.freeSlots():
            row = 'A'
            col = 1
        else:
            # We fill by rows
            t = self.tube_set.order_by('row','col').last()
            if self.ROWCOLS[self.racktype][1] == t.col:
                # The row is full, move one down,
                # we should not reach here if the rack is full
                row = rows[rows.index(t.row)+1]
                col = 1
            else:
                row = t.row
                col = t.col+1
        tube.rack = self
        tube.row = row
        tube.col = col
        tube.save()

        return True


    def insertSample(self,sample,pool=False):
        """
        Places a sample in the first tube in the rack that's not full
        The algorithm works in row first mode, i.e.:
        A1,A2,A3,...,H10,H11,H12
        """
        samplesTube = 1
        if pool:
            samplesTube = sample.batch.poolsize
        if self.isFull(samplesTube): return False
        # Find the first tube that's not full
        t = self.tube_set.order_by('row','col')
        t = t.annotate(samples=models.Count('sample'))
        if pool:
            t = t.filter(samples__lt=sample.batch.poolsize).first()
        else:
            t = t.filter(samples=0).first()
            if not t:
                t = Tube()
                t.identifier = sample.code
                self.insertTube(t)
        sample.tube = t
        sample.save()
        return True


    def __str__(self):
        return _('{0} with {1} samples {2}').format(
                 self.get_racktype_display(),
                 self.numSamples(),
                 self.identifier)

    def shortIdent(self):
        return '{0}...{1}'.format(self.identifier[:9],self.identifier[-9:])


    def save(self, *args, **kwargs):
        if not self.identifier or self.identifier.strip() == '':
            self.identifier = uuid.uuid4().hex
                
        super(Rack, self).save()


class Tube(models.Model):
    FILAS = [('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'),
             ('E', 'E'), ('F', 'F'), ('G', 'G'), ('H', 'H')]
    COLS = [(x,'%d' % x) for x in range(1,13)]
    identifier = models.CharField(verbose_name=_('identifier'),
                                  max_length=32, blank=True, null=True,
                                  db_index=True, editable=False)
    row = models.CharField(max_length=1,choices=FILAS,db_index=True,null=True)
    col = models.IntegerField(choices=COLS,db_index=True,null=True)
    rack = models.ForeignKey(Rack,blank=True,null=True)

    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)

    class Meta:
        ordering = ['createdOn']


    def __str__(self):
        return '{0} {1}:{2} {3}'.format(self.rack,self.row,self.col,
                                        len(self.sample_set.all()))


    def isEmpty(self):
        return len(self.sample_set.all()) == 0


    def numSamples(self):
        return len(self.sample_set.all())


    def clean(self):
        if self.row > self.rack.ROWCOLS[self.rack.racktype][0]:
            raise ValidationError({'row': _('Row %d does not exist' % self.row)})
        if self.col > self.rack.ROWCOLS[self.rack.racktype][1]:
            raise ValidationError({'col': _('Column %d does not exist' % self.col)})


    def save(self, *args, **kwargs):
        if not self.identifier or self.identifier.strip() == '':
            self.identifier = uuid.uuid4().hex

        super(Tube, self).save()


    pass


class Sample(models.Model):
    RESULTS = [('N',_('No')),('Y',_('Yes')),('U',_('Unclear'))]
    LEVELS = [('L',_('Low')),('M',_('Medium')),('H',_('High'))]
    identifier = models.CharField(verbose_name=_('identifier'),
                                  max_length=32, blank=True, null=True,
                                  db_index=True, editable=False)
    code = models.CharField(verbose_name=_('Sample code'), max_length=100, db_index=True)
    batch = models.ForeignKey(Batch)
    tube = models.ForeignKey(Tube,null=True,blank=True)
    finished = models.BooleanField(verbose_name=_('Processig completed'),
                                   db_index=True,default=False)
    result = models.CharField(verbose_name=_('Result'), max_length=1, db_index=True,
                              choices=RESULTS, blank=True, null=True, default='')

    # Control information
    createdOn = models.DateTimeField(_('Created on'),auto_now_add=True,
                                     db_index=True,editable=False)
    modifiedOn = models.DateTimeField(_('Modified on'),auto_now=True,
                                      db_index=True,editable=False)


    class Meta:
        ordering = ['batch','-modifiedOn']


    def __str__(self):
        return _('{0} en {1}').format(self.code,self.batch)


    def save(self, *args, **kwargs):
        if not self.identifier or self.identifier.strip() == '':
            self.identifier = uuid.uuid4().hex
        super(Sample, self).save()


    pass


