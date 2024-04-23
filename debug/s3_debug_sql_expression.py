# -*- coding: utf-8 -*-

import sqlalchemy as sa
import sqlalchemy.orm as orm
from uszipcode.model import SimpleZipcode, ComprehensiveZipcode

db_file_path = "/Users/sanhehu/.crawl_uszipcode/comprehensive.sqlite"
engine = sam.EngineCreator().create_sqlite(path=db_file_path)

Zipcode = ComprehensiveZipcode
with orm.Session(engine) as ses:
    stmt = sa.select(
        Zipcode.zipcode,
        Zipcode.major_city,
        Zipcode.state,
        Zipcode.population,
    ).where(
        Zipcode.population.between(10000, 50000)
    ).limit(10)
    res = ses.execute(stmt)

    # stmt = sa.select(Zipcode).limit(20)
    # res = ses.execute(stmt)
    # sam.pt.from_everything(Zipcode, ses)
    # n = Zipcode.count_all(ses)
    # print(n)

import json
from pathlib_mate import Path

with engine.connect() as connection:
    l = connection.execute(sa.select(Zipcode.__table__.c.zipcode)all()
p = Path(__file__).change(new_basename="data.json")
p.write_text(json.dumps(l))
