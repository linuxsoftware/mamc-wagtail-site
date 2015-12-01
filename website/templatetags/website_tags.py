from datetime import date
from collections import namedtuple
from django import template
from django.conf import settings
from django.template.loader import render_to_string

register = template.Library()


# settings value
@register.assignment_tag(takes_context=True)
def get_site_root(context):
    # NB this returns a core.Page, not the implementation-specific model used
    # so object-comparison to self will return false as objects would differ
    return context['request'].site.root_page


def has_menu_children(page):
    if page.get_children().live().in_menu():
        return True
    else:
        return False


@register.inclusion_tag('tags/website_menu.html', takes_context=True)
def website_menu(context):
    root = context['request'].site.root_page
    menuitems = root.get_children().live().in_menu()
    return {
        'menuitems': menuitems,
    }

# Retrieves the secondary links for the 'also in this section' links
# - either the children or siblings of the current page
@register.inclusion_tag('tags/secondary_menu.html', takes_context=True)
def secondary_menu(context, calling_page=None):
    pages = []
    if calling_page:
        pages = calling_page.get_children().live().in_menu()
        # If no children, get siblings instead
        if len(pages) == 0:
            pages = calling_page.get_siblings(inclusive=False).live().in_menu()
    return {
        'pages': pages,
        # required by the pageurl tag that we want to use within this template
        'request': context['request'],
    }


# Retrieves all live pages which are children of the calling page
#for standard index listing
@register.inclusion_tag(
    'tags/standard_index_listing.html',
    takes_context=True
)
def standard_index_listing(context, calling_page):
    pages = calling_page.get_children().live()
    return {
        'pages': pages,
        # required by the pageurl tag that we want to use within this template
        'request': context['request'],
    }


# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# -----------------------------------------------------------------------------

@register.inclusion_tag('tags/site_map.html',
                        takes_context=True)
def site_map(context):
    SiteItem = namedtuple("SiteItem", "title url level")
    site = context['request'].site
    root = site.root_page
    columns = []
    items = []
    height = 0
    for parent in root.get_children().live().in_menu():
        children = parent.get_children().live().in_menu()
        if height > 25 and height + 25 + len(children) * 14 > 110:
            columns.append(items)
            items = []
            height = 0
        items.append(SiteItem(parent.title, parent.relative_url(site), 1))
        height += 25
        if children:
            for child in children:
                if height == 0:
                    height = 25
                    items = [SiteItem("...", parent.relative_url(site), 1)]
                items.append(SiteItem(child.title, child.relative_url(site), 2))
                height += 14
                if height > 110:
                    columns.append(items)
                    items = []
                    height = 0
    if items:
        columns.append(items)
    return {'columns': columns}

