"""
The classes here provide support for using custom classes with
Matplotlib, e.g., those that do not expose the array interface but know
how to convert themselves to arrays.  It also supports classes with
units and units conversion.  Use cases include converters for custom
objects, e.g., a list of datetime objects, as well as for objects that
are unit aware.  We don't assume any particular units implementation;
rather a units implementation must provide the register with the Registry
converter dictionary and a `ConversionInterface`.  For example,
here is a complete implementation which supports plotting with native
datetime objects::

    import matplotlib.units as units
    import matplotlib.dates as dates
    import matplotlib.ticker as ticker
    import datetime

    class DateConverter(units.ConversionInterface):

        @staticmethod
        def convert(value, unit, axis):
            'Convert a datetime value to a scalar or array'
            return dates.date2num(value)

        @staticmethod
        def axisinfo(unit, axis):
            'Return major and minor tick locators and formatters'
            if unit!='date': return None
            majloc = dates.AutoDateLocator()
            majfmt = dates.AutoDateFormatter(majloc)
            return AxisInfo(majloc=majloc,
                            majfmt=majfmt,
                            label='date')

        @staticmethod
        def default_units(x, axis):
            'Return the default unit for x or None'
            return 'date'

    # Finally we register our object type with the Matplotlib units registry.
    units.registry[datetime.date] = DateConverter()

"""

from numbers import Number

import numpy as np
from numpy import ma
from decimal import Decimal

from matplotlib import cbook


class ConversionError(TypeError):
    pass


class AxisInfo(object):
    """
    Information to support default axis labeling, tick labeling, and limits.

    An instance of this class must be returned by
    `ConversionInterface.axisinfo`.
    """
    def __init__(self, majloc=None, minloc=None,
                 majfmt=None, minfmt=None, label=None,
                 default_limits=None):
        """
        Parameters
        ----------
        majloc, minloc : Locator, optional
            Tick locators for the major and minor ticks.
        majfmt, minfmt : Formatter, optional
            Tick formatters for the major and minor ticks.
        label : str, optional
            The default axis label.
        default_limits : optional
            The default min and max limits of the axis if no data has
            been plotted.

        Notes
        -----
        If any of the above are ``None``, the axis will simply use the
        default value.
        """
        self.majloc = majloc
        self.minloc = minloc
        self.majfmt = majfmt
        self.minfmt = minfmt
        self.label = label
        self.default_limits = default_limits


class ConversionInterface(object):
    """
    The minimal interface for a converter to take custom data types (or
    sequences) and convert them to values Matplotlib can use.
    """
    @staticmethod
    def axisinfo(unit, axis):
        """
        Return an `~units.AxisInfo` for the axis with the specified units.
        """
        return None

    @staticmethod
    def default_units(x, axis):
        """
        Return the default unit for *x* or ``None`` for the given axis.
        """
        return None

    @staticmethod
    def convert(obj, unit, axis):
        """
        Convert *obj* using *unit* for the specified *axis*.

        If *obj* is a sequence, return the converted sequence.  The output must
        be a sequence of scalars that can be used by the numpy array layer.
        """
        return obj

    @staticmethod
    def is_numlike(x):
        """
        The Matplotlib datalim, autoscaling, locators etc work with scalars
        which are the units converted to floats given the current unit.  The
        converter may be passed these floats, or arrays of them, even when
        units are set.
        """
        if np.iterable(x):
            for thisx in x:
                return isinstance(thisx, Number)
        else:
            return isinstance(x, Number)


class DecimalConverter(ConversionInterface):
    """
    Converter for decimal.Decimal data to float.
    """
    @staticmethod
    def convert(value, unit, axis):
        """
        Convert Decimals to floats.

        The *unit* and *axis* arguments are not used.

        Parameters
        ----------
        value : decimal.Decimal or iterable
            Decimal or list of Decimal need to be converted
        """
        # If value is a Decimal
        if isinstance(value, Decimal):
            return np.float(value)
        # else x is a list of Decimal
        else:
            converter = np.asarray
            if isinstance(value, ma.MaskedArray):
                converter = ma.asarray
            return converter(value, dtype=np.float)

    @staticmethod
    def axisinfo(unit, axis):
        # Since Decimal is a kind of Number, don't need specific axisinfo.
        return AxisInfo()

    @staticmethod
    def default_units(x, axis):
        # Return None since Decimal is a kind of Number.
        return None


class Registry(dict):
    """Register types with conversion interface."""

    def get_converter(self, x):
        """Get the converter interface instance for *x*, or None."""
        if hasattr(x, "values"):
            x = x.values  # Unpack pandas Series and DataFrames.
        if isinstance(x, np.ndarray):
            # In case x in a masked array, access the underlying data (only its
            # type matters).  If x is a regular ndarray, getdata() just returns
            # the array itself.
            x = np.ma.getdata(x).ravel()
            # If there are no elements in x, infer the units from its dtype
            if not x.size:
                return self.get_converter(np.array([0], dtype=x.dtype))
        try:  # Look up in the cache.
            return self[type(x)]
        except KeyError:
            try:  # If cache lookup fails, look up based on first element...
                first = cbook.safe_first_element(x)
            except (TypeError, StopIteration):
                pass
            else:
                # ... and avoid infinite recursion for pathological iterables
                # where indexing returns instances of the same iterable class.
                if type(first) is not type(x):
                    return self.get_converter(first)
        return None


registry = Registry()
registry[Decimal] = DecimalConverter()
