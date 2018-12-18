from django.http import HttpResponseRedirect
from sellerworx_api import SellerworxAPI
from django.contrib.auth.models import User
from django.contrib import auth
from datetime import datetime
from models import UserProfile, UserAccessTokens, AdminGroups, CustomerUserMapping
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
        """ this check the session if userid key exist, if not it will redirect to login page """
        response_data = {'data': {}, 'message': 'invalid user', 'status': 401}
        if not request.user.is_authenticated():
            if django_login_required(request):
                from oauth2_provider.models import AccessToken
                from datetime import datetime
                from django.utils import timezone
                now_aware = timezone.now()
                objs = AccessToken.objects.filter(token=request.META.get('HTTP_AUTHORIZATION',''))
                if objs and objs[0].expires > now_aware:
                    request.user = objs[0].application.user
                    return f(request, *args, **kwargs)
                else:
                    return HttpResponse(json.dumps(response_data), status=401)
            else:
                return HttpResponse(json.dumps(response_data), status=401)

        return f(request, *args, **kwargs)

    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap

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

