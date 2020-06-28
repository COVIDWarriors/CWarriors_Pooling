# -*- coding: utf-8 -*-
# vim:ts=4:expandtab:ai
# $Id: $

from django.utils.translation import ugettext_lazy as _

from django import forms
from django.conf import settings

from .models import Technician

TECHS=[(t.id,t.name) for t in Technician.objects.all()]

# this form started life as a simple file upload, but it is getting crammed
# at some point it will mutate into a more "Django compliant" beast :-)
class loadBatch(forms.Form):
    batchid = forms.CharField(max_length=32,required=False,
                    label=_('Batch identifier (leave blank to generate)'))
    samples = forms.FileField(label=_('Samples file'),required=False)
    poolsize = forms.IntegerField(label=_('Pool size'),
                                  initial=settings.POOL_TUBE_SAMPLES)
    techid = forms.IntegerField(label=_('Operator'),
                                widget=forms.Select(choices=TECHS))
