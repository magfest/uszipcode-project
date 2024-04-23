# -*- coding: utf-8 -*-

import json
import enum
import typing
import zlib
from functools import total_ordering
from pathlib_mate import Path
import sqlalchemy as sa
import sqlalchemy.orm as orm
from .state_abbr import (
    MAPPER_STATE_ABBR_SHORT_TO_LONG,
)
from haversine import haversine, Unit

Base = orm.declarative_base()

# -*- coding: utf-8 -*-

"""
Compressed json type.
"""

import zlib
import json
import sqlalchemy as sa


class CompressedJSONType(sa.types.TypeDecorator):
    """
    This column store json serialized object and automatically compress it
    in form of binary before writing to the database.

    This column should be a json serializable python type such as combination of
    list, dict, string, int, float, bool. Also you can use other standard
    json api compatible library for better serialization / deserialization
    support.

    **NOTE**, this type doesn't support JSON path query, it treats the object
    as a whole and compress it to save storage only.

    :param json_lib: optional, the json library you want to use. It should have
        ``json.dumps`` method takes object as first arg, and returns a json
        string. Should also have ``json.loads`` method takes string as
        first arg, returns the original object.

    .. code-block:: python

        # standard json api compatible json library
        import jsonpickle

        class Order(Base):
            ...

            id = Column(Integer, primary_key=True)
            items = CompressedJSONType(json_lib=jsonpickle)

        items = [
            {"item_name": "apple", "quantity": 12},
            {"item_name": "banana", "quantity": 6},
            {"item_name": "cherry", "quantity": 3},
        ]

        order = Order(id=1, items=items)
        with Session(engine) as ses:
            ses.add(order)
            ses.save()

            order = ses.get(Order, 1)
            assert order.items == items

            # WHERE ... = ... also works
            stmt = select(Order).where(Order.items==items)
            order = ses.scalars(stmt).one()
    """
    impl = sa.LargeBinary
    cache_ok = True

    _JSON_LIB = "json_lib"

    def __init__(self, *args, **kwargs):
        if self._JSON_LIB in kwargs:
            self.json_lib = kwargs.pop(self._JSON_LIB)
        else:
            self.json_lib = json
        super(CompressedJSONType, self).__init__(*args, **kwargs)

    def load_dialect_impl(self, dialect):
        return dialect.type_descriptor(self.impl)

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        return zlib.compress(
            self.json_lib.dumps(value).encode("utf-8")
        )

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return self.json_lib.loads(
            zlib.decompress(value).decode("utf-8")
        )

class ZipcodeTypeEnum(enum.Enum):
    """
    zipcode type visitor class.
    """
    Standard = "STANDARD"
    PO_Box = "PO BOX"
    Unique = "UNIQUE"
    Military = "MILITARY"


@total_ordering
class AbstractSimpleZipcode(Base):
    """
    Base class for Zipcode.
    """
    __abstract__ = True

    zipcode = sa.Column(sa.String, primary_key=True)
    zipcode_type = sa.Column(sa.String)
    major_city = sa.Column(sa.String)
    post_office_city = sa.Column(sa.String)
    common_city_list = sa.Column(CompressedJSONType)
    county = sa.Column(sa.String)
    state = sa.Column(sa.String)

    lat = sa.Column(sa.Float, index=True)
    lng = sa.Column(sa.Float, index=True)

    timezone = sa.Column(sa.String)
    radius_in_miles = sa.Column(sa.Float)
    area_code_list = sa.Column(CompressedJSONType)

    population = sa.Column(sa.Integer)
    population_density = sa.Column(sa.Float)

    land_area_in_sqmi = sa.Column(sa.Float)
    water_area_in_sqmi = sa.Column(sa.Float)

    housing_units = sa.Column(sa.Integer)
    occupied_housing_units = sa.Column(sa.Integer)

    median_home_value = sa.Column(sa.Integer)
    median_household_income = sa.Column(sa.Integer)

    bounds_west = sa.Column(sa.Float)
    bounds_east = sa.Column(sa.Float)
    bounds_north = sa.Column(sa.Float)
    bounds_south = sa.Column(sa.Float)

    _settings_major_attrs = "zipcode,zipcode_type,city,county,state,lat,lng,timezone".split(
        ",")

    @property
    def city(self):
        """
        Alias of ``.major_city``.
        """
        return self.major_city

    @property
    def bounds(self) -> dict:
        """
        Border boundary.
        """
        return {
            "west": self.bounds_west,
            "east": self.bounds_east,
            "north": self.bounds_north,
            "south": self.bounds_south,
        }

    @property
    def state_abbr(self) -> str:
        """
        Return state abbreviation, two letters, all uppercase.
        """
        return self.state.upper()

    @property
    def state_long(self) -> str:
        """
        Return state full name.
        """
        return MAPPER_STATE_ABBR_SHORT_TO_LONG.get(self.state.upper())

    def __bool__(self):
        """
        For Python3 bool() method.
        """
        return self.zipcode is not None

    def __lt__(self, other: 'AbstractSimpleZipcode'):
        """
        For ``>`` comparison operator.
        """
        if (self.zipcode is None) or (other.zipcode is None):
            raise ValueError(
                "Empty Zipcode instance doesn't support comparison.")
        else:
            return self.zipcode < other.zipcode

    def __eq__(self, other: 'AbstractSimpleZipcode'):
        """
        For ``==`` comparison operator.
        """
        return self.zipcode == other.zipcode

    def __hash__(self):
        """
        For hash() method
        """
        return hash(self.zipcode)

    def dist_from(self, lat: float, lng: float, unit: Unit = Unit.MILES):
        """
        Calculate the distance of the center of this zipcode from a coordinator.

        :param lat: latitude.
        :param lng: longitude.
        """
        return haversine((self.lat, self.lng), (lat, lng), unit=unit)

    def to_json(self, include_null: bool = True):
        """
        Convert to json.
        """
        data = self.to_OrderedDict(include_null=include_null)
        return json.dumps(data, indent=4)
    
    def glance(self):
        print(self.__repr__())


class AbstractComprehensiveZipcode(AbstractSimpleZipcode):
    __abstract__ = True

    polygon = sa.Column(CompressedJSONType)

    # Stats and Demographics
    population_by_year = sa.Column(CompressedJSONType)
    population_by_age = sa.Column(CompressedJSONType)
    population_by_gender = sa.Column(CompressedJSONType)
    population_by_race = sa.Column(CompressedJSONType)
    head_of_household_by_age = sa.Column(CompressedJSONType)
    families_vs_singles = sa.Column(CompressedJSONType)
    households_with_kids = sa.Column(CompressedJSONType)
    children_by_age = sa.Column(CompressedJSONType)

    # Real Estate and Housing
    housing_type = sa.Column(CompressedJSONType)
    year_housing_was_built = sa.Column(CompressedJSONType)
    housing_occupancy = sa.Column(CompressedJSONType)
    vacancy_reason = sa.Column(CompressedJSONType)
    owner_occupied_home_values = sa.Column(CompressedJSONType)
    rental_properties_by_number_of_rooms = sa.Column(CompressedJSONType)

    monthly_rent_including_utilities_studio_apt = sa.Column(CompressedJSONType)
    monthly_rent_including_utilities_1_b = sa.Column(CompressedJSONType)
    monthly_rent_including_utilities_2_b = sa.Column(CompressedJSONType)
    monthly_rent_including_utilities_3plus_b = sa.Column(CompressedJSONType)

    # Employment, Income, Earnings, and Work
    employment_status = sa.Column(CompressedJSONType)
    average_household_income_over_time = sa.Column(CompressedJSONType)
    household_income = sa.Column(CompressedJSONType)
    annual_individual_earnings = sa.Column(CompressedJSONType)

    sources_of_household_income____percent_of_households_receiving_income = sa.Column(
        CompressedJSONType)
    sources_of_household_income____average_income_per_household_by_income_source = sa.Column(
        CompressedJSONType)

    household_investment_income____percent_of_households_receiving_investment_income = sa.Column(
        CompressedJSONType)
    household_investment_income____average_income_per_household_by_income_source = sa.Column(
        CompressedJSONType)

    household_retirement_income____percent_of_households_receiving_retirement_incom = sa.Column(
        CompressedJSONType)
    household_retirement_income____average_income_per_household_by_income_source = sa.Column(
        CompressedJSONType)

    source_of_earnings = sa.Column(CompressedJSONType)
    means_of_transportation_to_work_for_workers_16_and_over = sa.Column(
        CompressedJSONType)
    travel_time_to_work_in_minutes = sa.Column(CompressedJSONType)

    # Schools and Education
    educational_attainment_for_population_25_and_over = sa.Column(
        CompressedJSONType)
    school_enrollment_age_3_to_17 = sa.Column(CompressedJSONType)


class SimpleZipcode(AbstractSimpleZipcode):
    __tablename__ = "simple_zipcode"


class ComprehensiveZipcode(AbstractComprehensiveZipcode):
    __tablename__ = "comprehensive_zipcode"
