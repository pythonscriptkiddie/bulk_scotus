from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from datetime import datetime, date

from sqlalchemy import Column, Integer, Numeric, String, Table, ForeignKey, Date, func, DateTime
from sqlalchemy.orm import relationship, synonym
from sqlalchemy.ext.declarative import declarative_base, synonym_for
from sqlalchemy.ext.associationproxy import association_proxy
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy.exc import InterfaceError, IntegrityError
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
import cmd2
from cmd2 import style, fg, bg

Base = declarative_base()


authorentries_table = Table('authorentries', Base.metadata,
    Column('entry_id', Integer(), ForeignKey("entries.entry_id"),
           primary_key=True),
    Column('author_id', Integer(), ForeignKey("authors.author_id"),
           primary_key=True)
)

keywordentries_table = Table('keywordentries', Base.metadata,
    Column('keyword_id', Integer(), ForeignKey("keywords.keyword_id"),
           primary_key=True),
    Column('entry_id', Integer(), ForeignKey("entries.entry_id"),
           primary_key=True)
)

roundupentries_table = Table('roundupentries', Base.metadata,
    Column('roundup_id', Integer(), ForeignKey("roundups.roundup_id"),
           primary_key=True),
    Column('entry_id', Integer(), ForeignKey("entries.entry_id"),
           primary_key=True)
)

roundupcategories_table = Table('roundupcategories', Base.metadata,
    Column('roundup_id', Integer(), ForeignKey("roundups.roundup_id"),
           primary_key=True),
    Column('category_id', Integer(), ForeignKey("categories.category_id"),
           primary_key=True)
)

roundupsections_table = Table('roundupsections', Base.metadata,
    Column('roundup_id', Integer(), ForeignKey("roundups.roundup_id"),
           primary_key=True),
    Column('section_id', Integer(), ForeignKey("sections.section_id"),
           primary_key=True)
)

class Case(Base):
    '''The actual Supreme Court cases'''
    __tablename__ = 'cases'
    case_id = Column(Integer(), primary_key=True)

class Roundup(Base):
    '''The roundups we export'''
    __tablename__ = 'roundups'
    roundup_id = Column(Integer(), primary_key=True)
    title = Column(String(200), index=True, nullable=False)
    introduction_id = Column(Integer(), ForeignKey('introductions.introduction_id'))
    start_date = Column(Date(), nullable=False)
    end_date = Column(Date(), nullable=False)
    release_date = Column(DateTime(), default=datetime.now())
    entries = relationship("Entry", secondary=lambda: roundupentries_table, back_populates='roundups')
    categories = relationship("Category", secondary=lambda: roundupcategories_table, back_populates='roundups')
    sections = relationship("Section", secondary=lambda: roundupsections_table, back_populates='roundups')
    introduction = relationship("Introduction", back_populates="roundups")
    id_value = synonym('roundup_id')
    second_item = synonym('introduction_id')
    
    def __repr__(self):
        return f'''Roundup(id='{self.roundup_id}', title='{self.title}')'''
    
    @property
    def cat_entries_roundup(self):
        '''This nested dictionary comprehension is used to create the actual docx roundups that are exported.
        Therefore, it has a nested structure that should not be used for anything else.'''
        return {section.name: {category.name:[i for i in self.entries if i.category.name == category.name] for category in self.categories if category.section_id == section.section_id} for section in self.sections}
    
    @property
    def html_cat_entries_roundup(self):
        '''This nested dictionary comprehension is used to create the actual html roundups that are exported.
        Therefore, it has a nested structure that - like the cat_entries_roundup property'''
        return {section.wrapped_html_string: {category.wrapped_html_string:[i for i in self.entries if i.category.name == category.name] for category in self.categories if category.section_id == section.section_id} for section in self.sections}
    
    @hybrid_property
    def name_value(self):
        '''The edit_roundup function in app.py edits the roundup name using
        this property'''
        return self.title
    
    @name_value.setter
    def name_value(self, name_value):
        self.title = name_value
        
    @property
    def wrapped_jsx_string(self):
        title = self.title.title()
        return f'''<p><i>{title}</i></p>\n'''

    
    #add new method to the class to enable 

class Introduction(Base):
    '''The introduction to roundups created by the database'''
    __tablename__ = 'introductions'
    introduction_id = Column(Integer(), primary_key=True)
    name = Column(String(100), index=True, nullable=False)
    text = Column(String(2000), nullable=False)
    roundups = relationship("Roundup", back_populates="introduction")
    
    def __repr__(self):
        return f'''Introduction(id='{self.introduction_id}', name='{self.name}')
Text: {self.text}'''

    @hybrid_property
    def id_value(self):
        return self.introduction_id
            
    @hybrid_property
    def wrapped_html_string(self):
        wrapped_string= f'<p><i>{self.text}</i></p>'
        print(wrapped_string)
        return wrapped_string

class Publication(Base):
    
    @classmethod
    def from_input(cls, url=None):
        title = input('Enter publication title: ')
        if url == None:
            url = input('Enter publication url: ')
        else:
            url = url
        return cls(title=title, url=url)
    
    __tablename__ = 'publications'
    publication_id = Column(Integer(), primary_key=True)
    title = Column(String(100), index=True, unique=True)
    url = Column(String(100), default=None, unique=True)
    entries = relationship("Entry", back_populates="publication")
    name=synonym('title')
    second_item=synonym('url') #we use this synonym for functions that affect more than one type of object
    
    def __repr__(self):
        return f'''Pub(id='{self.publication_id}' title='{self.title}', 'url={self.url})'''
    
    @hybrid_property
    def name_value(self):
        return self.title
    
    @hybrid_property
    def id_value(self):
        return self.publication_id
    
    @hybrid_property
    def items(self):
        return self.entries
    
class Author(Base):
    __tablename__ = 'authors'
    author_id = Column(Integer(), primary_key=True)
    author_name = Column(String(100))
    entries = relationship("Entry", secondary=lambda: authorentries_table)
    entry_names = association_proxy('entries', 'entry_name')
    name=synonym('author_name')
    
    def __repr__(self):
        return "Author(id='{self.author_id}' name='{self.author_name}')".format(self=self)
    
    @hybrid_property
    def id_value(self):
        return self.author_id
    
    @hybrid_property
    def name_value(self):
        return self.author_name
    
    @name_value.setter
    def name_value(self, name_value):
        self.author_name = name_value
    
    @hybrid_property
    def items(self):
        return self.entries
    
class Category(Base):
    
    @classmethod
    def from_input(cls, session, category_name=None):
        if category_name == None:
            name=input('Enter category name: ')
        else:
            name=category_name
        section_list = session.query(Section).all()
        print(section_list)
        section_id = input('Enter section id: ')
        return cls(name=name, section_id=section_id)
    
    __tablename__ = 'categories'
    
    category_id = Column(Integer(), primary_key=True)
    name = Column(String(255), index=True)
    section_id = Column(Integer(), ForeignKey('sections.section_id'))
    section=relationship("Section", back_populates="categories")
    entries = relationship("Entry", back_populates="category")
    roundups = relationship("Roundup", secondary=lambda: roundupcategories_table,
                            back_populates='categories')
    entry_names = association_proxy('entries', 'entry_name')
    second_item = synonym('section_id')
    
    def __repr__(self):
        return "Category(id='{self.id_value}' name='{self.name}', section={self.section_id})".format(self=self)
    
    def __contains__(self, item):
        return item in self.entries
    
    def __getitem__(self, item):
        return item in self.entries
    
    @property
    def wrapped_html_string(self):
        return f'''<p>{self.name}</p>'''

    @property
    def wrapped_jsx_string(self):
        title = self.name.title()
        return f'''<p><i>{title}</i></p>\n'''
    
   # @property
    def html_category_string(self, start_date, end_date):
        '''Single string to print to html and docx roundup files. Later, we will
        combine the category strings into section strings'''
        title = self.name.title()
        template = f'''<p><i>{title}</i></p>'''
        wrapString = lambda x: x.wrapped_html_string
        entry_map = map(wrapString,
                        (i for i in self.entries if (i.category_id== \
                            self.category_id) and (i.date >= start_date)) \
                        and (i.date <= end_date))
        result = [template]+[i for i in entry_map]
        return '\n'.join(result)
    
    @hybrid_property
    def id_value(self):
        return self.category_id
    
    @hybrid_property
    def name_value(self):
        '''Used so each datatype has a name value that is uniform across all datatypes'''
        return self.name
    
    @hybrid_property
    def items(self):
        '''Used to give each datatype a uniform value for any groups of items it contains'''
        return self.entries
    
class Section(Base):
    __tablename__ = 'sections'
    
    section_id = Column(Integer(), primary_key=True)
    name = Column(String(100))
    categories = relationship("Category", back_populates="section")
    roundups = relationship("Roundup", secondary=roundupsections_table,
                            back_populates="sections")
    
    def __repr__(self):
        return "Section(id='{self.id_value}', name='{self.name}')".format(self=self)

    @property
    def wrapped_html_string(self):
        return '''<p>{0}</p>'''.format(self.name)
    
    @property
    def wrapped_jsx_string(self):
        title = self.name.title()
        return f'''<p><b>{title}</b></p>\n'''
    
    @hybrid_property
    def name_value(self):
        return self.name
    
    @hybrid_property
    def id_value(self):
        return self.section_id
    
    @hybrid_property
    def items(self):
        return self.categories

class Entry(Base):
    '''We use the name entries to avoid overriding the Article object from the
    newspaper module'''
    __tablename__ = 'entries'

    entry_id = Column(Integer(), primary_key=True)
    entry_name = Column(String(100), index=True)
    entry_url = Column(String(255))
    description = Column(String(500))
    summary = Column(String(1500), default=None)
    date = Column(Date(), default=date.today())
    authors = relationship("Author", secondary=lambda: authorentries_table)
    author_names = association_proxy("authors", 'name')
    category_id = Column(Integer(), ForeignKey('categories.category_id'))
    category=relationship("Category", back_populates="entries")
    category_name = association_proxy('category', 'name')
    publication_id = Column(Integer(), ForeignKey('publications.publication_id'))
    publication = relationship("Publication", back_populates="entries")
    keywords = relationship("Keyword", secondary=lambda: keywordentries_table)
    keyword_list = association_proxy('keywords', 'word')
    roundups = relationship("Roundup", secondary=lambda: roundupentries_table, back_populates='entries')
    name=synonym('entry_name')
    
    def __init__(self, entry_name, entry_url, description, date,
                publication_id, category_id, keywords, summary=None, authors=None):
        self.entry_name = entry_name
        self.entry_url = entry_url
        self.description = description
        self.date = date
        self.category_id=category_id
        self.publication_id = publication_id
        self.authors=authors
        self.keywords=keywords
        self.summary=summary
        
    def __repr__(self):
        return f"""Entry(entry_id='{self.entry_id}',
entry_name='{self.entry_name}',
date='{self.date}',
entry_url='{self.entry_url}',
entry_id='{self.entry_id}',
category='{self.category}',
publication='{self.publication}',
authors='{self.authors}',
keywords='{self.keywords}',
description='{self.description}')"""
    
    @property
    def cmd2_style(self):
        '''Generates a representation of the object using the features of the
        cmd2 module'''
        return cmd2.style(text=self.__repr__(), bg=cmd2.bg.white,
                          fg=cmd2.fg.black, bold=False)
        
    @property
    def get_date_formatted(self):
        return f'{self.date.month}/{self.date.day}/{self.date.year}'
    
    @property
    def wrapped_html_string(self):
        '''For use when creating wrapped html strings for html files'''
        template = '<p><a href ={0}>{1}</a> ({2}) {3}</p>\n'
        return template.format(self.entry_url, self.entry_name, self.get_date_formatted,
                               self.description)
        
    @property
    def wrapped_jsx_string(self):
        '''For use when creating wrapped html strings for html files'''
        template = '<p><a href ="{0}">{1}</a> ({2}) {3}</p>\n'
        return template.format(self.entry_url, self.entry_name, self.get_date_formatted,
                               self.description)
    
    @hybrid_property
    def name_value(self):
        return self.entry_name
    
    @name_value.setter
    def name_value(self, new_name):
        self.entry_name = new_name
    
    @hybrid_property
    def id_value(self):
        return self.entry_id
    
    @hybrid_property
    def items(self):
        return self.keywords+self.authors

class Keyword(Base):
    __tablename__ = 'keywords'
    keyword_id = Column(Integer(), primary_key = True)
    word = Column(String(50), index=True, unique=True)
    entries = relationship("Entry", secondary=lambda: keywordentries_table)
    entry_names = association_proxy('entries', 'entry_name')
    name=synonym('word')
    #create table joining keywords and entries
    
    def __repr__(self):
        return "id={self.keyword_id} {self.word}".format(self=self)
    
    @hybrid_property
    def name_value(self):
        return self.word
    
    @hybrid_property
    def id_value(self):
        return self.keyword_id
    
    @hybrid_property
    def items(self):
        return self.entries
    
#Keywords will have a many to many relationship with entries and stories

class DataAccessLayer:
    def __init__(self):
        self.engine = None
        self.conn_string = 'sqlite:///scotus_cases.db'
        
    def connect(self):
        self.engine = create_engine(self.conn_string)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        
dal = DataAccessLayer()

#Roundup Objects Section

if __name__ == '__main__':
    #make sure we don't accidentally create a database when we don't want to 
    raise Exception('Not ready to start this database')