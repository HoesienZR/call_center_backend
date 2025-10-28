from rest_framework.pagination import PageNumberPagination

class LargePageSizePagination(PageNumberPagination):
    page_size = 100000
    page_size_query_param = 'page_size'
    max_page_size = 100000
