# ------------------------------------------------------------------------------
# Website models
# These are pages and things used across the site
# ------------------------------------------------------------------------------

from django.db import models
from wagtail.wagtailcore.models import Page
from wagtail.wagtailcore.fields import RichTextField, StreamField
from modelcluster.fields import ParentalKey
from wagtail.wagtailadmin.edit_handlers import (FieldPanel, MultiFieldPanel,
    InlinePanel, PageChooserPanel, StreamFieldPanel)
from wagtail.wagtailimages.edit_handlers import ImageChooserPanel
from wagtail.wagtaildocs.edit_handlers import DocumentChooserPanel
from wagtail.wagtailcore.blocks import CharBlock, RichTextBlock
from wagtail.wagtailimages.blocks import ImageChooserBlock
from wagtail.wagtailembeds.blocks import EmbedBlock
from website.coreutils import validate_only_one_instance

# ------------------------------------------------------------------------------
# A couple of abstract classes that contain commonly used fields
# ------------------------------------------------------------------------------

class LinkFields(models.Model):
    link_external = models.URLField("External link", blank=True)
    link_page = models.ForeignKey(
        'wagtailcore.Page',
        null=True,
        blank=True,
        related_name='+'
    )
    link_document = models.ForeignKey(
        'wagtaildocs.Document',
        null=True,
        blank=True,
        related_name='+'
    )

    @property
    def link(self):
        if self.link_page:
            return self.link_page.url
        elif self.link_document:
            return self.link_document.url
        else:
            return self.link_external

    panels = [
        FieldPanel('link_external'),
        PageChooserPanel('link_page'),
        DocumentChooserPanel('link_document'),
    ]

    class Meta:
        abstract = True

# Related links

class RelatedLink(LinkFields):
    title = models.CharField(max_length=255, help_text="Link title")

    panels = [
        FieldPanel('title'),
        MultiFieldPanel(LinkFields.panels, "Link"),
    ]

    class Meta:
        abstract = True

# ------------------------------------------------------------------------------
# Website Pages
# ------------------------------------------------------------------------------

class StreamPage(Page):
    class Meta:
        verbose_name = "Content Stream Page"

    content = StreamField([('heading',   CharBlock(classname="full title",
                                                   icon="title")),
                           ('paragraph', RichTextBlock(icon="pilcrow")),
                           ('image',     ImageChooserBlock(icon="image")),
                           ('embed',     EmbedBlock(icon="media")),
                          ], null=True, blank=True)
    content.help_text = "A page made up of blocks of text, images, video, etc."

    content_panels = Page.content_panels + [
        StreamFieldPanel('content')
        ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration")
        ]

# ------------------------------------------------------------------------------
class PlainPage(Page):
    class Meta:
        verbose_name = "Plain Text Page"

    content = RichTextField(default='', blank=True)
    content.help_text = "An area of text for whatever you like"

    content_panels = Page.content_panels + [
        FieldPanel('content', classname="full"),
        ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration")
        ]

# ------------------------------------------------------------------------------
# ------------------------------------------------------------------------------

