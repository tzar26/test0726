from datetime import *

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render
from django.views.generic import View

from . import models as kek_models


class OrderList(LoginRequiredMixin, View):

    @classmethod
    def get_orders_base_qs(cls, request):
        orders = kek_models.Orders.objects.filter()
        if request.user.search.search is not None and request.user.search.search != '':
            orders = orders.filter(
                Q(name__icontains=request.user.search.search) | Q(searchowners__icontains=request.user.search.search))
            return orders

        if request.user.search.goal:
            orders = orders.filter(goal=True)

        if request.user.search.favorite:
            orders_fav = [i.order.orderid for i in kek_models.Favorites.objects.filter(user=request.user)]
            orders = orders.filter(orderid__in=orders_fav)
        
        if request.user.search.manager is not None:
            order_res = [i.orderid.orderid for i in kek_models.Orderresponsible.objects.filter(user=request.user.search.manager)]
            res_qs = kek_models.Ordercomresponsible.objects.filter(user=request.user.search.manager).exclude(orderid__orderid__in=order_res)
            order_res = [i.orderid.orderid for i in res_qs]
            orders = orders.filter(orderid__in=order_res)

        if request.user.search.stage is not None:
            orders = orders.filter(stageid=request.user.search.stage)
        
        if request.user.search.company is not None:
            orders = orders.filter(Q(cityid=None) | Q(cityid=request.user.search.company))
        
        if request.user.search.customer != '':
            orders = orders.filter(searchowners__icontains=request.user.search.customer)
        return orders

    def get(self, request):
        orders = self.__class__.get_orders_base_qs(request)

        if request.GET['action'] == 'count':
            return JsonResponse({'count': orders.count()})

        start_idx = request.GET.get('start')
        if start_idx is not None:
            try:
                start_idx = int(start_idx)
            except ValueError:
                pass
        stop_idx = request.GET.get('stop')
        if stop_idx is not None:
            try:
                stop_idx = int(stop_idx)
            except ValueError:
                pass
        _slice = slice(start_idx, stop_idx)
        orders = orders.order_by('-reiting')[_slice]

        orders_ids = orders.values_list('orderid', flat=True)

        resp = [kek_models.CustomersList.objects.filter(orderid=i).order_by('customerid__title') for i in orders_ids]
        customers = [kek_models.CustomersList.objects.filter(orderid=i).order_by('customerid__title') for i in orders_ids]
        tasks = [kek_models.Comments.objects.filter(orderid__orderid=i, istask=1).exclude(complete=1).count() for i in orders_ids]
        favorite = [kek_models.Favorites.objects.filter(user=request.user, order__orderid=i).exists() for i in orders_ids]
        fcontact_item = lambda com: '' if com is None else com.createdat
        lastcontact = [fcontact_item(kek_models.Comments.objects.filter(orderid__orderid=i)) for i in orders_ids]

        context = {
            'orders': zip(orders, customers, favorite, lastcontact, task, resp),
            'Today': date.today()
        }
        return render(request, 'main/orders_list.html', context)


class CostList(LoginRequiredMixin, View):

    @classmethod
    def get_costs_base_qs(cls, request):
        costs = kek_models.Costs.objects.filter()
        if request.user.search.search is not None and request.user.search.search != '':
            costs = costs.filter(
                Q(description__icontains=request.user.search.search) | Q(
                    section__icontains=request.user.search.search) | Q(
                    orderid__name__icontains=request.user.search.search))
            return costs

        if request.user.search.goal is True:
            costs = costs.filter(orderid__goal=True)

        if request.user.search.favorite is True:
            costs_fav = [i.order.orderid for i in kek_models.Favorites.objects.filter(user=request.user)]
            costs = costs.filter(orderid__in=costs_fav)
        
        if request.user.search.manager is not None :
            costs = costs.filter(user=request.user.search.manager)
        
        if request.user.search.stage is not None:
            costs = costs.filter(orderid__stageid=request.user.search.stage)
        
        if request.user.search.company is not None:
            costs = costs.filter(Q(orderid__cityid=None) | Q(orderid__cityid=request.user.search.company))
        
        if request.user.search.customer != '':
            costs = costs.filter(orderid__searchowners__icontains=request.user.search.customer)
        return costs

    def get(self, request):
        costs = self.__class__.get_costs_base_qs(request)

        if request.GET['action'] == 'count':
            return JsonResponse({'count':costs.count()})

        start_idx = request.GET.get('start')
        if start_idx is not None:
            try:
                start_idx = int(start_idx)
            except ValueError:
                pass
        stop_idx = request.GET.get('stop')
        if stop_idx is not None:
            try:
                stop_idx = int(stop_idx)
            except ValueError:
                pass
        _slice = slice(start_idx, stop_idx)
        costs = costs.order_by('-createdat')[_slice]

        costs_ids = costs.values_list('id', flat=True)

        appr = [kek_models.Approvedlists.objects.filter(cost_id__id=i) for i in costs_ids]

        context = {
            'costs': zip(costs, appr),
            'Today': date.today()
        }
        return render(request, 'main/cost_list.html', context)
