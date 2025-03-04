from django.http import HttpResponseRedirect
from sellerworx_api import SellerworxAPI
from django.contrib.auth.models import User
from django.contrib import auth
from datetime import datetime
from models import UserProfile, UserAccessTokens, AdminGroups, CustomerUserMapping, StaffMaster
from django.contrib.auth.models import User,Permission,Group
from django.http import HttpResponse
from django.contrib.auth import authenticate, login, logout as wms_logout
from django.contrib.auth.decorators import login_required as django_login_required
import re
import json

def add_user_tokens(code, token, user_profile):
    """ Adding user tokens to DB """
    user_token = UserAccessTokens(user_profile=user_profile,
                                  code=code,
                                  access_token=token.get('access_token'),
                                  refresh_token=token.get('refresh_token'),
                                  token_type=token.get('token_type'),
                                  expires_in=token.get('expires_in'))
    user_token.save()

def update_token_details(code, token, user):
    """ Update token details on page refresh """
    user_token = UserAccessTokens.objects.get(user_profile__user_id=user.id)
    user_token.code = code
    user_token.access_token = token.get('access_token')
    user_token.refresh_token = token.get('refresh_token')
    user_token.save()

def get_user(seller_profile, code, token):
    """ Collecting User details with request.user """
    email = seller_profile['email']
    user = User.objects.filter(email=email)
    if user:
        return user[0]

    user = User.objects.create_user(username=seller_profile['name'],
                                    password='Hdrn^Miebach@10162015',
                                    email=seller_profile['email'])
    user.is_active = True
    user.save()

    phone = ''
    if seller_profile['phone']:
        phone = seller_profile['phone']
    prefix = re.sub('[^A-Za-z0-9]+', '', user.username)[:3].upper()
    user_profile = UserProfile(user=user, phone_number=phone,
                               is_active=seller_profile['active'], swx_id=seller_profile['id'],prefix=prefix)
    user_profile.save()
    add_user_tokens(code, token, user_profile)

    return user

def login_required(f):
    """Login Decorator """
    def wrap(request, *args, **kwargs):
        from oauth2_provider.models import AccessToken
        from datetime import datetime
        from django.utils import timezone
        now_aware = timezone.now()
        """ this check the session if userid key exist, if not it will redirect to login page """
        from rest_api.views.common import check_password_expiry
        response_data = {'data': {}, 'message': 'invalid user', 'status': 401}
        if not request.user.is_authenticated():
            if django_login_required(request):
                objs = AccessToken.objects.filter(token=request.META.get('HTTP_AUTHORIZATION',''))
                if objs and objs[0].expires > now_aware:
                    request.user = objs[0].application.user
                    return f(request, *args, **kwargs)
                else:
                    try:
                        temp_abs_url = request.get_full_path()
                        if temp_abs_url.split('/')[1] == 'api':
                            return HttpResponse(json.dumps(response_data), status=401)
                        else:
                            return HttpResponse(json.dumps(response_data))
                    except:
                        return HttpResponse(json.dumps(response_data))
            else:
                return HttpResponse(json.dumps(response_data))
        elif request.META.get('HTTP_AUTHORIZATION', None): 
            objs = AccessToken.objects.filter(token=request.META.get('HTTP_AUTHORIZATION',''))
            if objs and objs[0].expires > now_aware:
                request.user = objs[0].application.user
                return f(request, *args, **kwargs)
        else:
            password_expired = check_password_expiry(request.user)
            if password_expired:
                wms_logout(request)
                return HttpResponse(json.dumps(response_data))

        return f(request, *args, **kwargs)

    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap

def class_login_required(f):
    """Login Decorator """
    def wrap(classObj, *args, **kwargs):
        """ this check the session if userid key exist, if not it will redirect to login page """
        response_data = {'data': {}, 'message': 'invalid user', 'status': 401}
        if django_login_required(classObj.request):
            from oauth2_provider.models import AccessToken
            from datetime import datetime
            from django.utils import timezone
            now_aware = timezone.now()
            objs = AccessToken.objects.filter(token=classObj.request.META.get('HTTP_AUTHORIZATION',''))
            if objs and objs[0].expires > now_aware:
                classObj.request.user = objs[0].application.user
                return f(classObj, *args, **kwargs)
            else:
                try:
                    temp_abs_url = classObj.request.get_full_path()
                    if temp_abs_url.split('/')[1] in ['rest_api', 'api']:
                        return HttpResponse(json.dumps(response_data), status=401)
                    else:
                        return HttpResponse(json.dumps(response_data))
                except:
                    return HttpResponse(json.dumps(response_data))
        else:
            return HttpResponse(json.dumps(response_data))

            
def get_admin_user(f):
    def wrap(request, *args, **kwargs):
        user = ''
        admin_group = AdminGroups.objects.filter(user_id=request.user.id)
        if admin_group:
            user = admin_group[0].user
        else:
            groups_list = request.user.groups.all()
            for group in groups_list:
                group = AdminGroups.objects.filter(group_id=group.id)
                if group:
                    user = group[0].user
                    break
        if not user:
            user = request.user
            group,created = Group.objects.get_or_create(name=user.username)
            admin_dict = {'group_id': group.id, 'user_id': user.id}
            admin_group  = AdminGroups(**admin_dict)
            admin_group.save()
            user.groups.add(group)

        user_profile = UserProfile.objects.filter(user_id=request.user.id)
        if user_profile and user_profile[0].user_type == 'customer':
            cus_mapping = CustomerUserMapping.objects.filter(user_id=request.user.id)
            if cus_mapping:
                user_id = cus_mapping[0].customer.user
                user = User.objects.get(id=user_id)

        kwargs['user'] = user
        return f(request, *args, **kwargs)
    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap


def get_admin_multi_user(f):
    def wrap(request, *args, **kwargs):
        from rest_api.views.common import get_companies_list, get_company_id, get_related_users_filters
        user = ''
        admin_group = AdminGroups.objects.filter(user_id=request.user.id)
        if admin_group:
            user = admin_group[0].user
        else:
            groups_list = request.user.groups.all()
            for group in groups_list:
                group = AdminGroups.objects.filter(group_id=group.id)
                if group:
                    user = group[0].user
                    break
        if not user:
            user = request.user
            group,created = Group.objects.get_or_create(name=user.username)
            admin_dict = {'group_id': group.id, 'user_id': user.id}
            admin_group  = AdminGroups(**admin_dict)
            admin_group.save()
            user.groups.add(group)

        user_profile = UserProfile.objects.filter(user_id=request.user.id)
        if user_profile and user_profile[0].user_type == 'customer':
            cus_mapping = CustomerUserMapping.objects.filter(user_id=request.user.id)
            if cus_mapping:
                user_id = cus_mapping[0].customer.user
                user = User.objects.get(id=user_id)
        company_list = get_companies_list(user, send_parent=True)
        company_list = map(lambda d: d['id'], company_list)
        staff_obj = StaffMaster.objects.filter(email_id=request.user.username, company_id__in=company_list)
        if staff_obj.exists():
            users = User.objects.filter(username__in=list(staff_obj.values_list('plant__name', flat=True)))
            if not users:
                staff_obj = staff_obj[0]
                parent_company_id = get_company_id(user)
                company_id = staff_obj.company_id
                if parent_company_id == staff_obj.company_id:
                    company_id = ''
                users = get_related_users_filters(user.id, warehouse_types=['STORE', 'SUB_STORE'],
                                                       company_id=company_id)
            kwargs['users'] = users
        else:
            kwargs['users'] = User.objects.filter(id=user.id)
        return f(request, *args, **kwargs)
    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap


def get_admin_all_wh(f):
    def wrap(request, *args, **kwargs):
        from rest_api.views.common import get_companies_list, get_company_id, get_related_users_filters
        user = ''
        admin_group = AdminGroups.objects.filter(user_id=request.user.id)
        if admin_group:
            user = admin_group[0].user
        else:
            groups_list = request.user.groups.all()
            for group in groups_list:
                group = AdminGroups.objects.filter(group_id=group.id)
                if group:
                    user = group[0].user
                    break
        if not user:
            user = request.user
            group,created = Group.objects.get_or_create(name=user.username)
            admin_dict = {'group_id': group.id, 'user_id': user.id}
            admin_group  = AdminGroups(**admin_dict)
            admin_group.save()
            user.groups.add(group)

        user_profile = UserProfile.objects.filter(user_id=request.user.id)
        if user_profile and user_profile[0].user_type == 'customer':
            cus_mapping = CustomerUserMapping.objects.filter(user_id=request.user.id)
            if cus_mapping:
                user_id = cus_mapping[0].customer.user
                user = User.objects.get(id=user_id)
        company_list = get_companies_list(user, send_parent=True)
        company_list = map(lambda d: d['id'], company_list)
        staff_objs = StaffMaster.objects.filter(email_id=request.user.username, company_id__in=company_list)
        if staff_objs.exists():
            plant_users = User.objects.filter(username__in=list(staff_objs.values_list('plant__name', flat=True)))
            if not plant_users:
                staff_obj = staff_objs[0]
                parent_company_id = get_company_id(user)
                company_id = staff_obj.company_id
                if parent_company_id == staff_obj.company_id:
                    company_id = ''
                plant_users = get_related_users_filters(user.id, warehouse_types=['STORE', 'SUB_STORE'],
                                                       company_id=company_id)
            plant_list = list(plant_users.values_list('username', flat=True))
            plant_depts = get_related_users_filters(user.id, warehouse_types=['DEPT'],
                                                       warehouse=plant_list)
            dept_users = ''
            if staff_objs.exclude(department_type__isnull=True).values_list('department_type__name', flat=True):
                dept_users = plant_depts.filter(userprofile__stockone_code__in=list(staff_objs.values_list('department_type__name', flat=True)))
            else:
                if not dept_users:
                    staff_obj = staff_objs[0]
                    parent_company_id = get_company_id(user)
                    company_id = staff_obj.company_id
                    if parent_company_id == staff_obj.company_id:
                        company_id = ''
                    dept_users = plant_depts
            kwargs['users'] = plant_users | dept_users
        else:
            kwargs['users'] = User.objects.filter(id=user.id)
        return f(request, *args, **kwargs)
    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap



def check_customer_user(f):
    def wrap(request, *args, **kwargs):
        if request.user.is_authenticated():
            user_prof = UserProfile.objects.filter(user_id=request.user.id)
            if user_prof and user_prof[0].user_type == 'customer':
                wms_logout(request)
        return f(request, *args, **kwargs)
    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap


def check_process_status(f):
    from models import ProccessRunning
    def wrapper_func(request, *args, **kwargs):
        user = kwargs.get('user', '')
        try:
            process_status = ProccessRunning.objects.filter(process_name=f.__name__, user=user.id)
            if process_status.exists():
                if not process_status[0].running:
                    process_status.update(running=True)
                    response = f(request, *args, **kwargs)
                    process_status.update(running=False)
                else:
                    return HttpResponse("Process already running")

            else:
                ProccessRunning.objects.create(process_name=f.__name__, user=user.id,running=True)
                response = f(request, *args, **kwargs)
                process_status.update(running=False)
            return response
        except Exception as e:
            import traceback
            process_status.update(running=False)
            return HttpResponse("Internal Server Error")
    return wrapper_func

def check_user_process_status(f):
    from models import ProccessRunning
    def wrapper_func(request, *args, **kwargs):
        user = request.user
        try:
            process_status = ProccessRunning.objects.filter(process_name=f.__name__, user=user.id)
            if process_status.exists():
                if not process_status[0].running:
                    process_status.update(running=True)
                    response = f(request, *args, **kwargs)
                    process_status.update(running=False)
                else:
                    return HttpResponse("Process already running")

            else:
                ProccessRunning.objects.create(process_name=f.__name__, user=user.id,running=True)
                response = f(request, *args, **kwargs)
                process_status.update(running=False)
            return response
        except Exception as e:
            import traceback
            process_status.update(running=False)
            return HttpResponse("Internal Server Error")
    return wrapper_func

