### **Задача 1 (на написание кода)**

Сделать рефакторинг этого кода - https://gist.github.com/chepe4pi/3c5c2e4bab87fbf155dfdeaa18e2fc8f

Прислать результат. Объяснить какие проблемы были выявлены и какие подходы были использованы для улучшения кода. Какие рекомендации могли бы быть даны на код-ревью разработчику, который написал этот код.



"""
1. группировка и сортировка импортов: системные, фраймворк, приложение
* импорт из приложения потребует и группировку из 1го модуля (в представленном коде 2 импорта `from .models import ..`)
2. блок с импортами 3+ сущностей потребует в будущем:
* грязную историю в гит: удаление строки и добавление новой с отвлечением от самого изменения, от это проблемы не спасёт и оформление в
```
from kek import (
    lol1, lol2, lol3  # даже если
)
"""
from datetime import *

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404  # не используется get_object_or_404 в коде, возможно древний артефакт, линтер должен был показать
from django.views.generic import View

from .models import (
    Orders, Comments, Ordercomresponsible, CustomersList, Customer, Orderresponsible,
    Costs, Approvedlists, Favorites,  
    # завершающая строку запятая позволит при добавлении новой импортируемой сущности с новой строки не засорять 
    # изменения в коммите лишними данными, лишь добавляемая сущность, но добаслять надо тоже с зпт на конце
)
# при таком количестве импортируемых объектов (часть из которых могут потом перестать быть нужными и будут занимать ресурсы в locals)
# управлять импортом становится трудно
# я ипользую более гибкий вариант: `from . import models as kek_models` - а места использования, например Ordercomresponsible,
# меняю на kek_models.Ordercomresponsible по всему коду модуля, как только импортируемых сущностей становится больше трёх.
# В финальном варианте приведу к `from . import models as kek_models`, модель Customer как раз не использовалась в коде модуля в текущей реализации


class OrderList(LoginRequiredMixin, View):
    def get(self, request):
        ## orders = Orders.objects.all()  # пока не происходит никаких действий с выбокой из базы ещё ничего не берётся, не критично но лучше начинать не с all() а filter()
        orders = Orders.objects.filter()
        if request.user.search.search is not None and request.user.search.search != '':  # весь этот условный блок, 
                # логично выделить в базовое формирование выборки, сделаю в итоговом варианте
            orders = orders.filter(
                Q(name__icontains=request.user.search.search) | Q(searchowners__icontains=request.user.search.search))
        else:
            if request.user.search.goal:
                orders = orders.filter(goal=True)

            # визуально несвязанные условные блоки если разделены бланками воспринимаются лучше
            if request.user.search.favorite:
                ## fav = Favorites.objects.filter(user=request.user)
                ## orders_fav = []
                ## for i in fav:
                ##     orders_fav.append(i.order.orderid)
                # в случае если orderid не первичный ключ у order.orderid переписываем блок в списковое выражение
                ## почему списковое выражение лучше? в данном случае сразу выделяется необходимое кколичество памяти под хранение ссылок на элементы,
                ## append же периодически будет приводить к созданию более "длинного" списка и копирования в него старого и "добавления" нового элемента
                ## далее перепишем все такие циклы на вариант со списковым выражением (list comprehension)
                orders_fav = [i.order.orderid for i in Favorites.objects.filter(user=request.user)]
                # если же orderid первичный ключ у order.orderid то оптимальным решением будет
                # order_fav = Favorites.objects.filter(user=request.user).values_list('order__orderid', flat=True)

                orders = orders.filter(orderid__in=orders_fav)
            
            if request.user.search.manager is not None:
                ## res = Orderresponsible.objects.filter(user=request.user.search.manager)
                ## order_res = []
                ## for i in res:
                ##     order_res.append(i.orderid.orderid)
                order_res = [i.orderid.orderid for i in Orderresponsible.objects.filter(user=request.user.search.manager)]
                
                ## res = Ordercomresponsible.objects.filter(user=request.user.search.manager)
                ## res = res.exclude(orderid__orderid__in=order_res)
                # из-за длинны конструкции вынесем её в отдельную переменную - запрос не выполняется а лишь формируется конструкция, так что выделение под это переменной меньшее зло
                res_qs = Ordercomresponsible.objects.filter(user=request.user.search.manager).exclude(orderid__orderid__in=order_res)
                ## for i in res:
                ##    order_res.append(i.orderid.orderid)
                order_res = [i.orderid.orderid for i in res_qs]
                orders = orders.filter(orderid__in=order_res)

            if request.user.search.stage is not None:
                orders = orders.filter(stageid=request.user.search.stage)
            
            if request.user.search.company is not None:
                orders = orders.filter(Q(cityid=None) | Q(cityid=request.user.search.company))
            
            if request.user.search.customer != '':
                orders = orders.filter(searchowners__icontains=request.user.search.customer)

        # этапы подготовки выьборки, или выдача особых запросов лучше этапировать пустыми строками, для наглядности  
        if request.GET['action'] == 'count':
            return JsonResponse({'count': orders.count()})

        # следующий раунд вычислений - скорее всего тут нужен комметарий с большим смыслом по контексту, хотя это должен делать код сам за себя, 
        # я обозначил этим отделение нового блока кода
        # orders = orders.order_by('-reiting')[int(request.GET['start']):int(request.GET['stop'])]  # могут быть исключения: нечисловые параметры или отсутсвовать
        # предположу, что если в запросе нет старта или стопа, то указанная граница в выборке не будет использоваться, например, без стопа - всё от старта и до конца, без старта - всё от начала и до стопа
        # start_idx = request.GET['start']  # GET[] также не защищён от исключения django.utils.datastructures.MultiValueDictKeyError если не будет старта в запросе, так что лучше испольовать вариант:
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

        customers = []
        lastcontact = []
        resp = []
        favorite = []
        task = []
        for i in orders:
            resp.append( 
                # для лучшего чтения и избавления лишних orders.count() локальных выделений-удалений переменных, 
                # запишем добавление в список в таком виде тут и далее 
                Orderresponsible.objects.filter(orderid=i.orderid)
            )
            # формирование разных независимых сущностей разделил бланками

            # customerslist = CustomersList.objects.filter(orderid=i.orderid).order_by('customerid__title')  # экономия в памяти для order.count() локальных переменных
            # customers.append(customerslist)
            customers.append(
                CustomersList.objects.filter(orderid=i.orderid).order_by('customerid__title')
            )

            # if Comments.objects.filter(orderid=i).count() == 0:
            if not Comments.objects.filter(orderid=i).exists():
                lastcontact.append('')
            else:
                # lastcontact.append(Comments.objects.filter(orderid=i)[0].createdat)  
                lastcontact.append(
                    Comments.objects.filter(orderid=i).first().createdat  # оптимизация на уровне бд (first)
                ) 
            
            # task.append(Comments.objects.filter(orderid=i).filter(istask=1).exclude(complete=1).count())  # ничего криминального, но filter's лучше объединить
            task.append(
                Comments.objects.filter(orderid=i, istask=1).exclude(complete=1).count()
            ) 

            ## if Favorites.objects.filter(user=request.user).filter(order=i).count() == 0:  # 1. различные django-way пособия предлагают использовать для читабельности и по назначению .exists()
            # if not Favorites.objects.filter(user=request.user).filter(order=i).exists():  # 2. с точки зрения производительности (замерял timeit) лидера среди вариантов нет, хотя эту вилку можно заменить одной конструкцией теперь
            #    favorite.append(False)
            #else:
            #    favorite.append(True)
            # favorite.append(Favorites.objects.filter(user=request.user).filter(order=i).exists())  # 3.  
            favorite.append(
                Favorites.objects.filter(user=request.user, order=i).exists()
            )  # 4. объединил filter's и сделал по-читаемей
        # на данном этапе у нас осталась мегапроблема: постоянно растущие через создание новых (и выделение для них памяти) более длинных списков
        # по существу, все конструкции в списки используют у элемента из orders только .orderid (в случае если для выборки используется сам ордер, 
        # фильтр переписываем на выборку по этому ключевому полю), а значит всё начиная с `customers = []` переписываем в (с изменениями с комментариями):
        orders_ids = orders.values_list('orderid', flat=True)

        resp = [CustomersList.objects.filter(orderid=i).order_by('customerid__title') for i in orders_ids]
        customers = [CustomersList.objects.filter(orderid=i).order_by('customerid__title') for i in orders_ids]
        tasks = [Comments.objects.filter(orderid__orderid=i, istask=1).exclude(complete=1).count() for i in orders_ids]  # вот здесь мы вернулись к запросу
            # по ключу вместо объекта. также будет в favorite и комментах (контактах)
        favorite = [Favorites.objects.filter(user=request.user, order__orderid=i).exists() for i in orders_ids]
        fcontact_item = lambda com: '' if com is None else com.createdat
        lastcontact = [fcontact_item(Comments.objects.filter(orderid__orderid=i)) for i in orders_ids]
        # для оптимизации можно было переписать все эти списковые включения на итераторы, однако последующий зип данных нивелирует это преимущество в ограничении памяти

        # выделил финальный этап формирования контекста и ответа
        context = {
            'orders': zip(orders, customers, favorite, lastcontact, task, resp),
            'Today': date.today()
        }
        return render(request, 'main/orders_list.html', context)


class CostList(LoginRequiredMixin, View):
    def get(self, request):
        costs = Costs.objects.all()
        if request.user.search.search is not None and request.user.search.search != '':  # также в финальной версии, базовая выборка будет выделена в метод
            costs = costs.filter(
                Q(description__icontains=request.user.search.search) | Q(
                    section__icontains=request.user.search.search) | Q(
                    orderid__name__icontains=request.user.search.search))
        else:
            if request.user.search.goal is True:
                costs = costs.filter(orderid__goal=True)

            if request.user.search.favorite is True:
                ## fav = Favorites.objects.filter(user=request.user)
                ## orders_fav=[]
                ## for i in fav :
                ##     orders_fav.append(i.order.orderid)
                costs_fav = [i.order.orderid for i in Favorites.objects.filter(user=request.user)]
                costs = costs.filter(orderid__in=costs_fav)
            
            if request.user.search.manager is not None :
                costs = costs.filter(user=request.user.search.manager)
            
            if request.user.search.stage is not None:
                costs = costs.filter(orderid__stageid=request.user.search.stage)
            
            if request.user.search.company is not None:
                costs = costs.filter(Q(orderid__cityid=None) | Q(orderid__cityid=request.user.search.company))
            
            if request.user.search.customer != '':
                costs = costs.filter(orderid__searchowners__icontains=request.user.search.customer)

        if request.GET['action'] == 'count':
            return JsonResponse({'count': costs.count()})  # pepX должен быть пробел после :

        ## costs = costs.order_by('-createdat')[int(request.GET['start']):int(request.GET['stop'])]  # проверки входных параметров
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

        costs_ids = costs.values_list('id', flat=True)  # не зная модели Costs предположу что первичный ключ модели id, по нему делаю выборку, 
                # в реальности может быть другой ключ

        ## appr=[]
        ## for i in costs:
        ##    appr.append(Approvedlists.objects.filter(cost_id=i))
        appr = [Approvedlists.objects.filter(cost_id__id=i) for i in costs_ids]

        context = {
            'costs': zip(costs, appr),
            'Today': date.today()
        }
        return render(request, 'main/cost_list.html', context)