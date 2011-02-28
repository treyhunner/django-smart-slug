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
        self.reserved_slugs = kwargs.pop('reserved_slugs', [])
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

    def _get_slug_suffix(self, slug, i):
        if self.underscores:
            suffix = '_' * i
        else:
            suffix = '-%s' % i
        return '%s%s' % (slug[:self.max_length - len(suffix)], suffix)


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
            while base_qs.filter(**{self.attname: potential_slug}).count() > 0 or potential_slug in self.reserved_slugs:
                i += 1
                potential_slug = self._get_slug_suffix(slug, i)
        else:
            i = 0
            while potential_slug in self.reserved_slugs:
                i += 1
                potential_slug = self._get_slug_suffix(slug, i)

        setattr(instance, self.attname, potential_slug)
        return potential_slug

    def south_field_triple(self):
        "Returns a suitable description of this field for South."
        from south.modelsinspector import introspector
        field_class = "django.db.models.fields.SlugField"
        args, kwargs = introspector(self)
        return (field_class, args, kwargs)
