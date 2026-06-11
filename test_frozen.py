from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.models.word import Word
from app.routers.word import search_words
import utils

engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(bind=engine)
TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

with TestingSession() as session:
    session.add(Word(char='事業', code='22', jyutping='si6 jip6', length=2, finals='["i", "ip"]', initials='["s", "j"]'))
    session.add(Word(char='事業心', code='22', jyutping='si6 jip6 sam1', length=3))
    session.commit()

    print('Testing m2 mode for 事業')
    res = search_words(q='事業', mode='m2', db=session, limit=5, offset=0)
    print('Got', len(res), 'results')
    print('First few:', [r.get('char') if isinstance(r, dict) else getattr(r, 'char', None) for r in res[:3]])

    print('Testing syn mode')
    res2 = search_words(q='事業', mode='syn', db=session, limit=5, offset=0)
    print('Syn got', len(res2), 'results')
    print('Syn items:', [r.get('char') for r in res2])

print('All good, embedding ready?', utils.get_text_embedding.is_ready())
print('Test completed without crash.')