import datetime
from django.db.models.fields import SlugField
from django.db import models
from django.template.defaultfilters import slugify

class SmartSlugField(SlugField):
    __metaclass__ = models.SubfieldBase

    def __init__(self, *args, **kwargs):
        self.source_field = kwargs.pop('source_field', None)
        self.date_field = kwargs.pop('date_field', None)
        self.split_on_words = kwargs.pop('split_on_words', False)
        self.underscores = kwargs.pop('underscores', True)
        self.allow_duplicates = kwargs.pop('allow_duplicates', False)
        kwargs['unique'] = self.date_field is None and not self.allow_duplicates
        kwargs['editable'] = self.source_field is None
        super(SmartSlugField, self).__init__(*args, **kwargs)

    def _generate_date_query(self, dt):
        return {
            '%s__year' % self.date_field: dt.year,
            '%s__month' % self.date_field: dt.month,
            '%s__day' % self.date_field: dt.day
        }

    def slugify(self, content):
        return slugify(content)

    def pre_save(self, instance, add):
        potential_slug = getattr(instance, self.attname)

        if self.source_field:
            potential_slug = self.slugify(getattr(instance, self.source_field))
        
        model = instance.__class__

        if self.split_on_words and len(potential_slug) > self.max_length:
            pos = potential_slug[:self.max_length + 1].rfind('-')
            if pos > 0:
                potential_slug = potential_slug[:pos]

        potential_slug = slug = potential_slug[:self.max_length]
                
        if not self.allow_duplicates:
            if self.date_field:
                query = self._generate_date_query(getattr(instance, self.date_field))
            else:
                query = {}
            base_qs = model._default_manager.filter(**query)

            if instance.pk is not None:
                base_qs = base_qs.exclude(pk=instance.pk)

            i = 0
            while base_qs.filter(**{self.attname: potential_slug}).count() > 0:
                i += 1
                if self.underscores:
                    suffix = '_' * i
                else:
                    suffix = '-%s' % i
                potential_slug = '%s%s' % (slug[:self.max_length - len(suffix)], suffix)

        setattr(instance, self.attname, potential_slug)
        return potential_slug

try:
    from south.modelsinspector import add_introspection_rules
except ImportError:
    pass
else:
    add_introspection_rules([
        ([SmartSlugField], [],
            {
                "source_field": ["source_field", {"default": None}],
                "date_field": ["date_field", {"default": None}],
                "split_on_words": ["split_on_words", {"default": False}],
                "underscores": ["underscores", {"default": True}],
            },
        ),
    ], ["^smart_slug\.fields\.SmartSlugField"])
