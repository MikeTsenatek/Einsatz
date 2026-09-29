from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group

from .models import User
from .permissions import DEFAULT_GROUP_NAME


class StandardGroupUserAdmin(UserAdmin):
	def save_related(self, request, form, formsets, change):
		super().save_related(request, form, formsets, change)
		group = Group.objects.filter(name=DEFAULT_GROUP_NAME).first()
		if group is not None:
			form.instance.groups.add(group)


admin.site.register(User, StandardGroupUserAdmin)
