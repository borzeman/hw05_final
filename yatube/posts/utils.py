from django.core.paginator import Paginator


POST_NUM = 10


def get_page_paginator(request, post_list, items_per_page=POST_NUM):
    paginator = Paginator(post_list, items_per_page)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return page_obj
