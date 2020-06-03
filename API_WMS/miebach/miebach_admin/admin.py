from django.contrib import admin

from models import SKURelation, SKUMaster, UserBrand, Brands, GroupStage, ProductionStages, UserStages, UserProfile, ProductionStages, AdminGroups,\
	GroupBrand, GroupStages, OrderDetail, BarcodeSettings, CompanyMaster, Integrations

# Register your models here.


@admin.register(SKUMaster)
class SKUMasterAdmin(admin.ModelAdmin):
    search_fields = ['sku_code', 'user']
    list_display = ('sku_code', 'user')

@admin.register(SKURelation)
class SKUGroupAdmin(admin.ModelAdmin):
    pass

@admin.register(OrderDetail)
class OrderDetailAdmin(admin.ModelAdmin):
    search_fields = ['order_id', 'sku_code', 'user']
    list_display = ('id', 'original_order_id', 'order_id', 'order_code', 'sku', 'title', 'user')


#@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    search_fields = ['user__username']
    list_display = ('get_user_profile_user',)

    def get_user_profile_user(self, obj):
        return obj.user.username

#@admin.register(BarcodeSettings)
class BarcodeSettingsAdmin(admin.ModelAdmin):
    search_fields = ['user__username']
    list_display = ('user', 'format_type', 'show_fields')


class CompanyMasterAdmin(admin.ModelAdmin):
    search_fields = ['company_name']
    list_display = ('company_name', 'creation_date', 'parent')

admin.site.register(Integrations)
admin.site.register(UserBrand)
admin.site.register(Brands)
admin.site.register(UserStages)
admin.site.register(UserProfile, UserProfileAdmin)
admin.site.register(ProductionStages)
admin.site.register(AdminGroups)
admin.site.register(GroupBrand)
admin.site.register(GroupStages)
admin.site.register(BarcodeSettings, BarcodeSettingsAdmin)
admin.site.register(CompanyMaster, CompanyMasterAdmin)
