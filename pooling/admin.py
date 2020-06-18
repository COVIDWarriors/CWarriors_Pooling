# -*- coding: utf-8 -*-
# vim:ts=4:expandtab:ai
# $Id: $
from django.contrib import admin

# Register your models here.
from .models import *


class TechnicianAdmin(admin.ModelAdmin):
    model = Technician
    list_display = ['id','identifier','name']
    list_display_links = ['id','identifier']
    fieldsets = (
        (None, {'fields': ('name',),},),
    )


admin.site.register(Technician,TechnicianAdmin)


class RobotAdmin(admin.ModelAdmin):
    model = Robot
    list_editable = ['ip','connected']
    list_display = ['id','identifier','ip','connected']
    list_display_links = ['id','identifier']
    fieldsets = (
        (None, {'fields': ('identifier','ip','connected'),},),
    )


admin.site.register(Robot,RobotAdmin)


class SampleAdmin(admin.TabularInline):
    model = Sample
    extra = 1
    hidden_fields = ('createdOn','modifiedOn','identifier',)


class BatchAdmin(admin.ModelAdmin):
    model = Batch
    inlines = [SampleAdmin]
    list_display = ['id','identifier','technician','started','finished']
    list_filter = ['technician','started','finished']
    list_editable = ['technician']
    list_display_links = ['id','identifier']
    fieldsets = (
        (None, {'fields': ('technician','started','finished',),},),
    )

admin.site.register(Batch,BatchAdmin)


class TubeAdmin(admin.TabularInline):
    model = Tube
    extra = 1
    hidden_fields = ('createdOn','modifiedOn',)


class RackAdmin(admin.ModelAdmin):
    model = Rack
    inlines = [TubeAdmin]
    list_display = ['id','identifier','racktype','numSamples',
                    'position','createdOn']
    list_filter = ['racktype','position']
    list_editable = ['racktype']
    list_display_links = ['id','identifier']
    fieldsets = (
        (None, {'fields': ('racktype','position'),},),
    )


admin.site.register(Rack,RackAdmin)


