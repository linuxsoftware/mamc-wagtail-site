# ------------------------------------------------------------------------------
# Homepage models
# This is just for the homepage, which is a bit special
# ------------------------------------------------------------------------------

from django.db import models

from wagtail.wagtailcore.models import Page, Orderable
from wagtail.wagtailcore.fields import RichTextField
from wagtail.wagtailadmin.edit_handlers import FieldPanel, MultiFieldPanel, \
    InlinePanel, PageChooserPanel
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from modelcluster.fields import ParentalKey


class HomePageHighlight(Orderable):
    homepage = ParentalKey('home.HomePage', related_name='highlights')
    title = models.CharField("Title", max_length=80, blank=True)
    blurb = RichTextField(default='', blank=True)
    image = models.ForeignKey('wagtailimages.Image',
                              null=True,
                              blank=True,
                              on_delete=models.SET_NULL,
                              related_name='+')
    page  = models.ForeignKey('wagtailcore.Page',
                              null=True,
                              blank=True,
                              related_name='+')

    panels = [FieldPanel('title', classname="full title"),
              FieldPanel('blurb', classname="full"),
              ImageChooserPanel('image'),
              PageChooserPanel('page'), ]


class HomePage(Page):
    parent_page_types = []
    class Meta:
        verbose_name = "Homepage"

    banner_image = models.ForeignKey('wagtailimages.Image',
                                     null=True,
                                     blank=True,
                                     on_delete=models.SET_NULL,
                                     related_name='+')
    banner_image.help_text = "A big wide image (at least 1440x650px) to "\
                             "grab the viewer's attention"

    welcome = RichTextField(default='', blank=True)
    welcome.help_text = "A short introductory message"
    content = RichTextField(default='', blank=True)
    content.help_text = "An area of text for whatever you like"


    # HomePage is a bit different to other pages as the title is not displayed
    content_panels = [
        ImageChooserPanel('banner_image'),
        FieldPanel('welcome', classname="full"),
        InlinePanel('highlights', label="Highlights"),
        FieldPanel('content', classname="full"),
        ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration")
        ]
