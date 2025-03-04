from django.http import HttpResponseRedirect
from sellerworx_api import SellerworxAPI
from django.contrib.auth.models import User
from django.contrib import auth
from datetime import datetime
from miebach_admin.models import UserProfile, UserAccessTokens, AdminGroups
from django.contrib.auth.models import User, Permission, Group


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
    user_profile = UserProfile(user=user, phone_number=phone,
                               is_active=seller_profile['active'], swx_id=seller_profile['id'])
    user_profile.save()
    add_user_tokens(code, token, user_profile)

    return user


def login_required(f):
    """Login Decorator """

    def wrap(request, *args, **kwargs):
        """ this check the session if userid key exist, if not it will redirect to login page """
        response_data = {message: "fail"}
        if request.isAuthenticated():
            response_data.message = "success"

        user.backend = 'django.contrib.auth.backends.ModelBackend'
        auth.login(request, user)

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
            group, created = Group.objects.get_or_create(name=user.username)
            admin_dict = {'group_id': group.id, 'user_id': user.id}
            admin_group = AdminGroups(**admin_dict)
            admin_group.save()
            user.groups.add(group)

        kwargs['user'] = user
        return f(request, *args, **kwargs)

    wrap.__doc__ = f.__doc__
    wrap.__name__ = f.__name__
    return wrap
