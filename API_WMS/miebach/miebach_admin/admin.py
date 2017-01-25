from django.contrib import admin

from models import SKURelation, SKUMaster, UserBrand, Brands, GroupStage, ProductionStages, UserStages, UserProfile, ProductionStages, AdminGroups,\
	GroupBrand, GroupStages

# Register your models here.


@admin.register(SKUMaster)
class SKUMasterAdmin(admin.ModelAdmin):
    search_fields = ['sku_code']

@admin.register(SKURelation)
class SKUGroupAdmin(admin.ModelAdmin):
    pass

admin.site.register(UserBrand)
admin.site.register(Brands)
admin.site.register(UserStages)
admin.site.register(UserProfile)
admin.site.register(ProductionStages)
admin.site.register(AdminGroups)
admin.site.register(GroupBrand)
admin.site.register(GroupStages)
