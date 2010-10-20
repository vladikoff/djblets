from django.conf import settings
from django.core.urlresolvers import get_resolver, NoReverseMatch, reverse

from djblets.extensions.base import ExtensionHook, ExtensionHookPoint


class URLHook(ExtensionHook):
    """
    A hook that installs custom URLs. These URLs reside in a project-specified
    parent URL.
    """
    __metaclass__ = ExtensionHookPoint

    def __init__(self, extension, patterns):
        ExtensionHook.__init__(self, extension)
        self.patterns = patterns

        # Install these patterns into the correct urlconf.
        if hasattr(settings, "EXTENSION_ROOT_URLCONF"):
            parent_urlconf = settings.EXTENSION_ROOT_URLCONF
        elif hasattr(settings, "SITE_ROOT_URLCONF"):
            parent_urlconf = settings.SITE_ROOT_URLCONF
        else:
            # Fall back on get_resolver's defaults.
            parent_urlconf = None

        self.parent_resolver = get_resolver(parent_urlconf)
        assert self.parent_resolver

        self.parent_resolver.url_patterns.extend(patterns)

    def shutdown(self):
        super(URLHook, self).shutdown()

        for pattern in self.patterns:
            self.parent_resolver.url_patterns.remove(pattern)


class TemplateHook(ExtensionHook):
    """
    A hook that renders a template at hook points defined in another template.
    """
    __metaclass__ = ExtensionHookPoint

    _by_name = {}

    def __init__(self, extension, name, template_name, apply_to=[]):
        ExtensionHook.__init__(self, extension)
        self.name = name
        self.template_name = template_name
        self.apply_to = apply_to

        if not name in self.__class__._by_name:
            self.__class__._by_name[name] = [self]
        else:
            self.__class__._by_name[name].append(self)

    def shutdown(self):
        super(TemplateHook, self).shutdown()

        print "shutting down %s" % self.name
        self.__class__._by_name[self.name].remove(self)

    def applies_to(self, context):
        """Returns whether or not this TemplateHook should be applied given the
        current context.
        """

        # If apply_to is empty, this means we apply to all - so
        # return true
        if not self.apply_to:
            return True

        # Extensions Middleware stashes the kwargs into the context
        kwargs = context['request']._djblets_extensions_kwargs
        current_url = context['request'].path_info

        # For each URL name in apply_to, check to see if the reverse
        # URL matches the current URL.
        for applicable in self.apply_to:
            try:
                reverse_url = reverse(applicable, args=(), kwargs=kwargs)
            except NoReverseMatch:
                # It's possible that the URL we're reversing doesn't take
                # any arguments.
                try:
                    reverse_url = reverse(applicable)
                except NoReverseMatch:
                    # No matches here, move along.
                    continue

            # If we got here, we found a reversal.  Let's compare to the
            # current URL
            if reverse_url == current_url:
                return True

        return False

    @classmethod
    def by_name(cls, name):
        if name in cls._by_name:
            return cls._by_name[name]

        return []