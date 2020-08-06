import itertools as it
import functools
import pprint
import warnings
import re
from datetime import date, timedelta
from collections import Counter
import cmd2 #let's import it so we can pass the cmd interface as an object
from typing import Any, List
import spacy
import newspaper as np
from newspaper import Article
from GoogleNews import GoogleNews
from dateutil.parser import parse
from dateutil.parser import ParserError
import IPython
from sqlalchemy import func
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.exc import IntegrityError
import docx
from docx.enum.dml import MSO_THEME_COLOR_INDEX
import BTCInput4 as btc
from roundup_db1 import Entry, Category, Keyword, Publication, Author, Section, Introduction, Roundup
from roundup_db1 import DataAccessLayer

'''FUNCTIONS FOR cmd2 MODULE STYLES these functions need to be converted to
regular def functions.
These functions are called throughout the module to produce repeatedly used 
styles'''

def black_white_bg(x):
    '''Takes text input, and returns a cmd2 style with
    black text with a white background. Bold is not
    active so in practice the background is gray'''
    return cmd2.style(text=x, fg=cmd2.fg.black, bg=cmd2.bg.white, bold=False)

def black_white_bg_bold(x):
    '''Takes text input, and returns a cmd2 style with
    black text with a white background but bold, so the
    background is white'''
    return cmd2.style(text=x, fg=cmd2.fg.black, bg=cmd2.bg.white, bold=True)

def error_msg(x):
    '''Takes a string and returns a cmd2 style with a red background
    and yellow text'''
    return cmd2.style(text=x, fg=cmd2.fg.yellow, bg=cmd2.bg.red, bold=True)

def std(text, cmdobj, bold=False):
    '''Takes text and a cmd object as input and then returns a cmd2 style
    with the default color settings as the result'''
    return cmd2.style(text=text, fg=cmdobj.foreground_color,
                      bg=cmdobj.background_color, bold=bold)

#SPECIAL DATE HANDLING SECTION ------

def make_date_range(sdate: date, edate: date) -> List:
    '''Returns a date range when we are sending it two STRINGS'''
    delta = edate-sdate
    dates = (sdate+timedelta(i) for i in range(delta.days+1))
    dates = [i.date() for i in dates]
    return dates

def range_from_dates(sdate: date, edate: date) -> List:
    '''Returns a date range when we are sending it two DATES'''
    delta = edate-sdate
    dates = (sdate+timedelta(i) for i in range(delta.days+1))
    dates = [i for i in dates]
    return dates

#--------------------------------------
    
#Error message works not only for error messages but anything intended to warn
#for example the delete function will make extensive use of this


#create section (legacy code)

def add_category(session, category_name):
    result = get(session=session, model=Category, name=category_name)
    if result != None:
        print('Category exists')
        return
    else:
        new_category = Category.from_input(category_name=category_name, session=session)
    confirm_choice = btc.read_int_ranged(f'Add {new_category.name}? 1 to add, 2 to cancel: ', 1, 2)
    if confirm_choice == 1:
        session.add(new_category)
        session.commit()
        print(f'{new_category.name} added to database')#.format(new_category.name))
    elif confirm_choice == 2:
        print('Category add cancelled')
        return

def new_cat_with_entry(session, cmdobj, category_name, section_id):
    '''Creates a new category when we're in the process of making an entry'''
    make_cat = lambda x, y: Category(name=x, section_id=y)
    new_category = make_cat(x=category_name, y=section_id)
    try:
        session.add(new_category)
        session.commit()
        return None
    except Exception as e:
        cmdobj.poutput(e)
        cmdobj.poutput(error_msg(f'Category creation failed for {category_name}'))
        return None
    

def add_item(session, search_type, new_name):
    """session is the current active session, search_type is the type of item, while
    new_name is the current type of item to add"""
    new_name=new_name.lower()
    search_types = {'author': Author, 'keyword': Keyword,
             'section': Section}
    result = get(session=session, model=search_types[search_type], name=new_name)
    if result != None:
        print('Item exists')
    else:
        confirm_choice = btc.read_int_ranged(f'Add {new_name}? 1 to add, 2 to cancel', 1, 2)
        if confirm_choice == 1:
            new_item=get_or_create(session=session, model=search_types[search_type], name=new_name)
            print(f'{new_item} added to database')#.format(new_item))
        elif confirm_choice == 2:
            print('add cancelled')
            return
    
def add_pub_or_cat(session, cmdobj, add_type, new_name, second_item):
    '''use this one for the CLI'''
    add_type = add_type.lower()
    add_types = {'publication': Publication, 'category': Category}
    result = get(session=session, model=add_types.get(add_type), name=new_name, second_item=second_item)
    if result != None:
        cmdobj.poutput(f'{add_type} exists')
        #print(f'{add_type} exists')
        cmdobj.poutput(result)
        print(result)
        return
    else:
        confirm_choice = cmdobj.select([(1, f'Add {new_name}'),
                                    (2, f'cancel')])
        #confirm_choice = btc.read_int_ranged(f'Add {new_name}? 1 to add, 2 to cancel', 1, 2)
        if confirm_choice == 1:
            get_or_create(session, model=add_types.get(add_type), name=new_name,
                      second_item=second_item)
        elif confirm_choice == 2:
            cmdobj.poutput(error_msg(f'{add_type} add cancelled'))
            #print(f'{add_type} add cancelled').format(add_type))
            return

def add_roundup(args, session, cmdobj):    #fix bug whereby every new roundup only sets its articles when it is created
    '''Takes args from the ui.py module and will create a roundup,
    right now it currently prints them.
    params:
        
    args - the arguments passed from the ui.py module
    session - the session object passed to the function from ui.py
    cmdobj - the cmd2 object passed to the function
    
    '''
    cmdobj.poutput(args)
    args.title = ' '.join(args.title)
    args.date_range[0] = parse(args.date_range[0]).date()
    args.date_range[1] = parse(args.date_range[1]).date()
    entries = [i for i in session.query(Entry).filter(Entry.date >= args.date_range[0],
                                                      Entry.date <= args.date_range[1])]
    categories = [i for i in session.query(Category).all()]
    sections = [i for i in session.query(Section).all()]
    new_roundup = Roundup(title=args.title,
                          introduction_id = args.introduction_id,
                          start_date=args.date_range[0],
                          end_date=args.date_range[1],
                          entries = entries, sections=sections,
                          categories=categories)
    session.add(new_roundup)
    #cmdobj.poutput(new_roundup)
    session.commit()
    cmdobj.poutput(new_roundup)
    cmdobj.poutput(cmd2.style('Roundup added to database', bg=cmd2.bg.blue,
                              fg=cmd2.fg.white, bold=True))
    
#modify articles
    
def add_keyword_to_article(session, cmdobj, new_keyword, entry_id=None):
    """Add a keyword to an existing article, the keyword is appended to the article's
    keywords attribute"""
    if entry_id == None:
        entry_id = btc.read_int_adv(prompt='Find an entry by ID: ', cmdobj=cmdobj)
    entry_result = session.query(Entry).filter(Entry.entry_id==entry_id).scalar()
    if entry_result != None:
        cmdobj.poutput(std('Entry found: ', cmdobj=cmdobj))
        cmdobj.poutput(std(entry_result, cmdobj=cmdobj))
        #print('Entry found: ')
        #print(entry_result)
        edit_choice = cmdobj.select([(1, f'Add {new_keyword} to this article'),
                                    (2, 'Cancel')])
        #edit_choice = btc.read_int_ranged(f'Add {new_keyword} to this article? (1 for yes, 2 for no): ', 1, 2)
        if edit_choice == 1:
            keyword_result = session.query(Keyword).filter(Keyword.word.like(f'%{new_keyword}%')).all()
            if len(keyword_result) >= 1:
                cmdobj.poutput(std('Keyword exists', cmdobj=cmdobj))
                #print('Keyword exists')
                cmdobj.poutput(std(keyword_result, cmdobj=cmdobj))
                #print(keyword_result)
                cmdobj.poutput(std('Entry found:', cmdobj=cmdobj))
                #print('Entry found:')
                #print(entry_result)
                cmdobj.poutput(std(entry_result, cmdobj=cmdobj))
                keywords = it.chain(keyword_result)
                while True:
                        #we do this loop if the keyword exists
                    try:
                        #item = next(keywords)
                        #print(item)
                        cmdobj.poutput(item := next(keywords))
                    except StopIteration:
                        cmdobj.poutput(cmd2.style('No more keywords left',
                                bg=cmd2.bg.red, fg=cmd2.fg.yellow))
                        #print('No more keywords left')
                    cmdobj.poutput(std('Is this the keyword you want?', cmdobj=cmdobj))
                    item_choice = cmdobj.select([(1, 'yes'), (2, 'continue'), (3, 'quit')])
                    #item_choice = btc.read_int_ranged('Is this the keyword you want? (1-yes, 2-continue, 3-quit)', 
                     #                                 1, 3)
                    #1 select
                    if item_choice == 1:
                        try:
                            assert item not in entry_result.keywords
                        except AssertionError:
                            cmdobj.poutput(error_msg('keyword already attached to article'))
                            cmdobj.poutput(std('Returning to main menu', cmdobj=cmdobj))
                            #print('Keyword already attached to article')
                            #print('Returning to main menu')
                            return
                        entry_result.keywords.append(item)
                        session.commit()
                        cmdobj.poutput(std('Keyword added successfully', cmdobj=cmdobj))
                        #print('Keyword added successfully')
                        break
                    elif item_choice == 2:
                            #continue
                        continue
                    elif item_choice == 3:
                        cmdobj.poutput(error_msg('Keyword add cancelled, return to main menu'))
                        return
            elif len(keyword_result) ==0:
                cmdobj.poutput(error_msg('Keyword does not exist'))
                #print('Keyword does not exist')
                kw = Keyword(word=new_keyword)
                cmdobj.poutput(std(f'Create {kw} as a new keyword for ? {entry_result.entry_name}',
                        cmdobj=cmdobj))
                make_keyword_choice = cmdobj.select(enumerate(['Yes', 'No'], 1))
                #make_keyword_choice = btc.read_int_ranged(f'Create {kw} as a new keyword for ? {entry_result.entry_name} (1 yes, 2 no)',1, 2)
                if make_keyword_choice == 1:
                    entry_result.keywords.append(kw)
                    session.commit()
                    cmdobj.poutput(std('Keyword add completed', cmdobj=cmdobj))
                    #print('Keyword add completed')
                elif make_keyword_choice == 2:
                    cmdobj.poutput(error_msg('Add keyword cancelled'))
                    #print('Add keyword cancelled')
                    return
        elif edit_choice == 2:
            cmdobj.poutput(error_msg('Keyword edit cancelled, return to main menu'))
            #print('Keyword edit cancelled, returning to main menu')
            return
    elif entry_result == None:
        cmdobj.poutput(error_msg('Entry not found, returning to main menu'))
        return

def update_keywords(session, cmdobj, entry_id):
    entry_to_edit = session.query(Entry).filter(Entry.entry_id == entry_id).one()
    entry_for_updating = np.Article(entry_to_edit.entry_url)
    entry_for_updating.build()
    nlp=spacy.load('en_core_web_sm')
    doc=nlp(entry_for_updating.text)
    permitted_labels = {'PERSON', 'LOC', 'GPE', 'ORG', 'PRODUCT', 'EVENT'}
    for i in doc.ents:
        print(error_msg(i))
    new_keywords = list({i.text for i in doc.ents if i.label_ in permitted_labels})
    new_keywords = [get_or_create(session=session, model=Keyword,
                                          word=i) for i in new_keywords]
    for item in new_keywords:
        entry_to_edit.keywords.append(item)
        session.commit()
    #args_dict['keywords'] = [get_or_create(session=session, model=Keyword,
    #                                      word=i) for i in new_keywords]

def delete_entry_keyword(session, cmdobj, entry_id):
    '''Delete a keyword from an existing article by popping it from the keyword list'''
    entry_result = session.query(Entry).filter(Entry.entry_id==entry_id).scalar()
    if entry_result != None:
        article_keywords = it.cycle(entry_result.keywords)
        while True:
            pprint.pprint(entry_result.keywords)
            activeItem = next(article_keywords)
            delete_choice = cmdobj.select(enumerate([f'Delete {activeItem}',
                                'Continue', 'Return to main menu'],1))
            #print('Enter 1 to delete keyword, 2 to continue, 3 to exit to main menu')
            #delete_choice = btc.read_int_ranged(f'Delete {activeItem} from the keywords?', 1, 3)
            if delete_choice == 1:
                entry_result.keywords.remove(activeItem)
                session.commit()
            elif delete_choice == 2:
                continue
            elif delete_choice == 3:
                print('Returning to main menu')
                break
    else:
        print('Not found, return to main menu')
        return

def make_article(article: str) -> np.Article:
    article = np.Article(article)
    article.build()
    return article

def get_or_create(session, model, **kwargs):
    '''If an object is present in the database, it returns the object.
    Otherwise, it creates a new instance of that object'''
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance

#read section - functions associated with reading items

    
def get(session, model, **kwargs):
    '''If an object is present in the database, it returns the object.
    Otherwise, it creates a new instance of that object'''
    instance = session.query(model).filter_by(**kwargs).scalar()
    return instance
    
def display_categories(section_id, cmdobj):
    query = dal.session.query(Category)
    if section_id != None:
        query = query.filter(Category.section_id == section_id)
    query = query.all()
    cmdobj.poutput(std('Categories', cmdobj=cmdobj, bold=True))
    cat_map = map(str, query)
    cmdobj.poutput(std('\n'.join(cat_map), cmdobj=cmdobj, bold=False))

def display_sections(cmdobj=None):
    query = dal.session.query(Section).all()
    section_map = map(str, query)
    if cmdobj==None:
        print('Sections: ')
        print('\n'.join(section_map))
    else:
        cmdobj.poutput(std('Sections:', cmdobj=cmdobj))
        cmdobj.poutput(std('\n'.join(section_map), cmdobj=cmdobj))

def get_description():
    description = input('Enter article description (max 500 characters): ')
    return description
        
def get_sections():
    '''Return a list of all the sections in the program'''
    query = dal.session.query(Section).all()
    return query

def get_categories(session, section_id=None):
    '''Return a list of all the categories in the program'''
    query = session.query(Category)
    if section_id == None:
        query = session.query(Category).all()
    else:
        query = query.filter(Category.section_id == section_id).all()
    return query

def article_count(session):
    query = session.query(Category.name, func.count(Entry.entry_id))
    query= query.outerjoin(Entry).group_by(Category.name)
    query = query.order_by(func.count(Entry.entry_id))
    query = query.all()
    for row in query[::-1]:
        print(row)
    undescribed_articles=session.query(Entry).filter(Entry.description.like('%not specified%')).all()
    print('Undescribed articles', len(undescribed_articles))
        
def date_range_count(start_date, end_date, session, cmdobj):
    '''Combine date_range_count and article_count'''
    #continue formatting the entry count - 05/08/2020
    try:
        start_date, end_date = parse(start_date), parse(end_date)
        start_date = start_date.date()
        end_date = end_date.date()
    except IndexError as e:
            print(e)
            return
    #get categories with articles
    query = session.query(Category.name, func.count(Entry.entry_id))
    query= query.outerjoin(Entry).group_by(Category.name)
    query = query.filter(Entry.date >= start_date, end_date <= end_date)
    query = query.order_by(func.count(Entry.entry_id))
    query = query.all()
    #get number of undescribed articles
    undesc = session.query(Entry).filter(Entry.date >= start_date) #get number of undescribed articles
    undesc = undesc.filter(Entry.date <= end_date)
    undesc = undesc.filter(Entry.description.like('%not specified%')).all()
    undesc_num = len(undesc)
    total = functools.reduce(lambda x, y: x+y,[row[1] for row in query])
    for category in session.query(Category).all():
        arts = session.query(Entry).filter(Entry.category_id == category.category_id,
                                           Entry.date >= start_date,
                                           Entry.date <= end_date).all()
        if len(arts) == 0:
            query.insert(0, (category.name, 0))
    cmdobj.poutput(cmd2.style(text='Date range article count',
                            bg=cmdobj.background_color,
                            fg=cmdobj.foreground_color,
                            bold=True))
    rows = (str(row[1])+' '+str(row[0]) for row in sorted(query, key=lambda x: x[1],
                                                          reverse=True))
    #we reverse the order becuase we want the names to be in order
    result_map = map(str, rows)
    cmdobj.poutput(cmd2.style(text='\n'.join(result_map), bg=cmdobj.background_color,
                              fg=cmdobj.foreground_color))
    #format the dates for the article count
    date_format = lambda x: cmd2.style(text=x.strftime("%B %d, %Y (%A)"),
                                                       bg=cmdobj.background_color,
                                                       fg=cmdobj.foreground_color,
                                                       bold=True)
    sd_f, ed_f = date_format(start_date), date_format(end_date)
    result_str = str(total) + ' ' + f'articles total from {sd_f} to {ed_f}'
    cmdobj.poutput(result_str)
    cmdobj.poutput(std(f'Undescribed articles: {undesc_num}',
                       cmdobj=cmdobj, bold=True))
    
def articles_needed(start_date, end_date, session):
    min_articles_cat = 5
    '''Combine date_range_count and article_count'''
    try:
        start_date, end_date = parse(start_date), parse(end_date)
        start_date = start_date.date()
        end_date = end_date.date()
        print('start date:', start_date)
        print('end date:', end_date)
    except IndexError as e:
            print(e)
            return
    query = session.query(Category.name, func.count(Entry.entry_id))
    query= query.outerjoin(Entry).group_by(Category.name)
    query = query.filter(Entry.date >= start_date, end_date <= end_date)
    query = query.order_by(func.count(Entry.entry_id))
    query = query.all()
    articles_needed = {}
    for row in query[::-1]:
        if row[1] < 5:
            articles_needed[row[0]] = (min_articles_cat - row[1])
    pprint.pprint(articles_needed)
    
def find_introduction(args, session, cmdobj):
    '''Takes arguments from the ui.py module
    args includes args.introduction_id, args.name, and args.text
    only args.introduction_id will be implemented at this present stage'''
    if not args.introduction_id:
        raise Exception(error_msg('No introduction ID found'))
    else:
        get_intro = lambda x: session.query(Introduction).filter(Introduction.introduction_id==x).first()
        intro_result = get_intro(args.introduction_id)
        cmdobj.poutput(black_white_bg(intro_result))
    
def find_entry(args, session, cmdobj):
    '''Takes arguments about the entry from the ui and returns an it.cycle
    object containing all the entries that meet that criteria'''
    if args.entry_id and args.id_range:
        raise Exception('Must be either id or id range')
    elif args.date and args.date_range:
        raise Exception('Must be either date or date range')
    else:
        query = session.query(Entry)
        if args.category_id:
            query = query.filter(Entry.category_id == args.category_id)
        if args.category_name:
            print(args.category_name)
            cat_name = ' '.join(args.category_name)
            cat_query = session.query(Category)
            cat_query = cat_query.filter(Category.name.like(f'%{cat_name}%')).first()
            print(cat_query)
            cat_id = cat_query.id_value
            query = query.filter(Entry.category_id == cat_id)
        if args.id_range:
            query = query.filter(Entry.entry_id >= args.id_range[0],
                                    Entry.entry_id <= args.id_range[1])
        if args.entry_id:
            query = query.filter(Entry.entry_id == args.entry_id)
        if args.date:
            date = parse(args.date).date()
            query = query.filter(Entry.date == date)
        if args.date_range:
            query = query.filter(Entry.date >= parse(args.date_range[0]).date(),
                                    Entry.date <= parse(args.date_range[1]).date())
        if args.url:
            query = query.filter(Entry.entry_url.like(f'%{args.url}%'))
        if args.title:
            query = query.filter(Entry.entry_name.like(f'%{args.title}%'))
        if args.publication_id:
            query = query.filter(Entry.publication_id==args.publication_id)
        if args.publication_title:
            pub_query = session.query(Publication).filter(Publication.title.like(f'%{args.publication_title}%')).first()
            pub_id = pub_query.publication_id
            query=query.filter(Entry.publication_id == pub_id)
        result = query.all()
        result_total = len(result)
        if result_total == 0:
            cmdobj.poutput(error_msg('No entries found'))
            #print('no entries found')
            return
        result_cycle = it.cycle(result)
        cmdobj.poutput(std(f'{result_total} entries found', cmdobj=cmdobj))
        info_choice = cmdobj.select([(1, 'View results'), (2, 'Cancel')])
        if info_choice == 1:
            while next_item := next(result_cycle):
                continue_choice = cmdobj.select([(1, f'view {next_item.name}'), (2, 'continue'),
                                        (3, 'quit')])
                if continue_choice == 1:
                    cmdobj.poutput(next_item.cmd2_style)
                    edit_choice = cmdobj.select([(1, f'Edit {next_item.name}'),
                            (2, 'Continue'), (3, 'Quit')])
                    if edit_choice == 1:
                        edit_entry(session=session, entry_id=next_item.entry_id, cmdobj=cmdobj)
                    elif edit_choice == 2:
                        continue
                    elif edit_choice == 3:
                        cmdobj.poutput(error_msg('Edit cancelled, return to main menu'))
                        return
                elif continue_choice == 2:
                    continue
                elif continue_choice == 3:
                    cmdobj.poutput(std('Returning to main menu', cmdobj=cmdobj))
                    break

def find_section(args, session, cmdobj):
    '''Takes data inputted by the user in ui.py and returns a section'''
    query = session.query(Section)
    if args.section_id:
        query = query.filter(Section.section_id==args.section_id)
    if args.name:
        query = query.filter(Section.name.like(f'%{args.name}%'))
    result = query.all()
    result_total = len(result)
    if result_total == 0:
        cmdobj.poutput(error_msg('No sections found'))
        #print('no sections found')
        return
    result_cycle = it.cycle(result)
    cmdobj.poutput(std(f'{result_total} sections found', cmdobj=cmdobj))
    #print(f'{result_total} sections found')
    info_choice = cmdobj.select([(1, 'View results'), (2, 'Cancel')])
    #info_choice = btc.read_int_ranged('1 to view results, 2 to cancel: ', 1, 2)
    if info_choice == 1:
        while next_item := next(result_cycle):
            continue_choice = cmdobj.select([(1, 'View next'), (2, 'Quit')])
            #continue_choice = btc.read_int_ranged('1 to view next, 2 to quit: ', 1, 2)
            cmdobj.poutout(std(next_item, cmdobj=cmdobj))
            #print(next(result_cycle).name)
            if continue_choice == 1:
                cmdobj.poutput(std(next_item, cmdobj=cmdobj))
                #print(next(result_cycle))
            elif continue_choice == 2:
                cmdobj.poutput(std('Returning to main menu', cmdobj=cmdobj))
                #print('returning to main menu')
                break
                
def find_keyword(args, session, cmdobj):
    query = session.query(Keyword)
    if args.keyword_id:
        query = query.filter(Keyword.keyword_id==args.keyword_id)
    if args.word:
        query = query.filter(Keyword.word.like(f'%{args.word}%'))
    result = query.all()
    result_total = len(result)
    if result_total == 0:
        cmdobj.poutput(error_msg('No keywords found'))
        #print('no keywords found')
        return
    result_cycle = it.cycle(result)
    print(f'{result_total} keywords found')
    info_choice = btc.read_int_ranged('1 to view results, 2 to cancel: ', 1, 2)
    if info_choice == 1:
        while True:
            continue_choice = btc.read_int_ranged('1 to view next, 2 to quit: ', 1, 2)
            print(next(result_cycle).name)
            if continue_choice == 1:
                print(next(result_cycle))
            elif continue_choice == 2:
                print('returning to main menu')
                break 
            
def find_roundup(args, session, cmdobj):
    '''Finds a roundup for the search roundup function in ui.py
    Takes an argparse namespace (args) and a 
    as an argument'''
    query = session.query(Roundup).filter(Roundup.roundup_id == args.roundup_id).first()
    cmdobj.poutput(black_white_bg(query))
    
def get_category(category_name, session):
    '''Gets the category for the create article function'''
    if type(category_name) == list:
        category_name = ' '.join(category_name)
    query = session.query(Category).filter(Category.name.like(f'%{category_name}%')).first()
    print(query)
    return query

def get_category_name(category_name, session):
    '''Gets the category for the create article function'''
    query = session.query(Category).filter(Category.name.like(f'%{category_name}%')).first()
    return query

def get_category_by_id(category_id, session):
    '''Returns the category directly from the database to the cmd2 application'''
    query = session.query(Category).filter(Category.category_id==category_id).first()
    return query

def find_category(args, session, cmdobj):
    query = session.query(Category)
    if args.category_id:
        query = query.filter(Category.category_id == args.category_id)
    if args.category_name:
        cmdobj.poutput(std(args.category_name, cmdobj=cmdobj))
        #print(args.category_name)
        category_name = ' '.join(args.category_name)
        #print(category_name)
        cmdobj.poutput(category_name)
        query = query.filter(Category.name.like(f"%{category_name}%"))
    if args.section_id:
        query = query.filter(Category.section_id == args.section_id)
    result = query.all()
    result_total = len(result)
    if result_total == 0:
        cmdobj.poutput(std('No categories found', cmdobj=cmdobj))
        #print('no categories found')
        return
    result_cycle = it.cycle(result)
    cmdobj.poutput(std(f'{result_total} categories found', cmdobj=cmdobj))
    #print(f'{result_total} categories found')
    info_choice = cmdobj.select(enumerate(['View results', 'Cancel'], 1))

    #info_choice = btc.read_int_ranged('1 to view results, 2 to cancel: ', 1, 2)xw
    if info_choice == 1:
        while next_item := next(result_cycle):
            try:
                continue_choice = cmdobj.select(enumerate(['View next', 'Quit'], 1))
                #continue_choice = btc.read_int_ranged('1 to view next, 2 to quit: ', 1, 2)
                cmdobj.poutput(std(next_item.name, cmdobj=cmdobj))
                if continue_choice == 1:
                    cmdobj.poutput(std(next_item, cmdobj=cmdobj))
                    #print(next(result_cycle))
                elif continue_choice == 2:
                    cmdobj.poutput(std('Returning to main menu', cmdobj=cmdobj))
                    #print('returning to main menu')
                    break
            except StopIteration:
                cmdobj.poutput(error_msg('No more categories remaining'))

def find_publication(args, session, cmdobj):
    '''Takes arguments from the user and finds a publication, which the user
    can then edit. The arguments included in args are:
        
    args.publication_id: publication id
    args.title: publication title
    args.url: publication link'''
    query = session.query(Publication)
    if args.publication_id:
        query = query.filter(Publication.id_value == args.publication_id)
    if args.title:
        query = query.filter(Publication.title == args.title)
    if args.url:
        query = query.filter(Publication.url.like(f'%{args.url}%'))
    result = query.all()
    cmdobj.poutput(std(result, cmdobj=cmdobj))
    #print(result)
    results = it.cycle(result)
    active_item = next(results)
    edit_opts = [f'Edit publication {active_item.title}', 'Cancel']
    edit_choice = cmdobj.select(opts=enumerate(edit_opts, 1))
    #edit_choice = btc.read_int_ranged(prompt=f'Edit publication {active_item.title} (1-y, 2-n)? ',
    #                                  min_value=1,max_value=2)
    if edit_choice == 1:
        warnings.warn('Edit publication under development')
        edit_single_pub(session=session, active_item=active_item, cmdobj=cmdobj)
    elif edit_choice == 2:
        cmdobj.poutput(error_msg('Returning to main menu'))                 

def edit_single_pub(session, active_item, cmdobj):
    '''Edit a single publication'''
    while True:
        print(f'''\n
Publication ID: {active_item.id_value}
Title: {active_item.name_value}
Link: {active_item.url}''')
        edit_opts = ['Edit title', 'Edit link', 'Next publication']
        edit_choice = cmdobj.select(enumerate(edit_opts, 1))
        #edit_choice = btc.read_int_ranged('Edit title - 1, Edit link - 2, 3-next_publication: ', 1, 3)
        if edit_choice == 1:
            view_articles_choice = cmdobj.select(enumerate(['View entries for this publication',
                                        'Skip'], 1))
            #view_articles_choice = btc.read_int_ranged('Type 1 to view entries for this publication, 2 to skip', 1, 2)
            if view_articles_choice == 1:
                for i in active_item.entries:
                    cmdobj.poutput(std(i, cmdobj=cmdobj))
                    #print(i)
            else:
                cmdobj.poutput(std('Entries display not needed', cmdobj=cmdobj))
                #print('Entries display not needed')
            new_title = btc.read_text_adv('Enter new title or "." to cancel: ',
                                cmdobj=cmdobj, bg=cmdobj.background_color,
                                fg=cmdobj.foreground_color)
            #print(new_title)
            cmdobj.poutput(std(new_title, cmdobj=cmdobj))
            if new_title != '.': 
                active_item.title = new_title
                session.commit()
        elif edit_choice == 2:
            new_url = btc.read_text_adv('Enter new url or "." to cancel: ',
                                cmdobj=cmdobj, bg=cmdobj.background_color,
                                fg=cmdobj.foreground_color)
            if new_url == ".":
                cmdobj.poutput(error_msg('Edit cancelled'))
                #print('Edit cancelled')
                break
            else:
                edit_second_item(session=session, model='publication',
                                 id_value=active_item.id_value,
                                 new_second_value=new_url)
        elif edit_choice == 3:
            break
       
def get_articles_for_roundup(start_date, end_date, category_id):
    '''
    Do not mess with this function without absolute certainty that you will
    not break the roundup generation process.
    '''
    query = dal.session.query(Category)
    query = query.filter(Category.category_id == category_id)
    query = query.first()
    return query

def get_entries_by_category(session, line):
    result = session.query(Category)
    result = result.filter(Category.name.like(f'%{line}%'))
    try:
        result = result.one()
    except MultipleResultsFound:
        print('Multiple results found')
        potentials = it.cycle(result)
        while True:
            potential_result = next(potentials)
            print(potential_result)
            result_choice = btc.read_bool(decision='is this the category? (y-yes, n-no): ',
                                         yes='y', no='n',
                                         yes_option='select', no_option='continue')
            if result_choice == True:
                result = potential_result
                break
            else:
                continue
    print(result)
    review_choice = btc.read_bool(decision=f'View articles from {result}',
                                       yes='y', no='n',
                                       yes_option='continue', no_option='cancel')
    print(review_choice)
    if review_choice == True:
        entries_by_cat = it.cycle(result.entries)
        while True:
            continue_choice = btc.read_bool(decision=f'View next article from {result}',
                                    yes='y', no='n',
                                    yes_option='continue', no_option='cancel')
            if continue_choice == True:
                print(next(entries_by_cat))
            elif continue_choice == False:
                print('Returning to main menu')
                break

#EDIT Publication
    
def edit_pub(args, session, cmdobj):
    query=session.query(Publication)
    if args.publication_id:
        query=query.filter(Publication.id_value == args.publication_id)
    elif args.id_range:
        query = query.filter(Publication.id_value >= args.id_range[0],
                             Publication.id_value <= args.id_range[1])
    elif args.title:
        title_value = ' '.join(args.title)
        query=query.filter(Publication.title.like(f"{title_value}"))
    elif args.url:
        query=query.filter(Publication.url.like(f'{args.url}'))
    result = query.all()
    #result_total = len(result)
    if len(result) == 0: #if we have no results in the result list
        #print('no publications found')
        cmdobj.poutput(error_msg('No publications found'))
        return
    result_cycle = it.cycle(result)
    #remaining_pubs = len(result)
    cmdobj.poutput(std(f'{len(result)} remaining publications', cmdobj=cmdobj))
    while active_item := next(result_cycle):
        try:
            cmdobj.poutput(std(active_item, cmdobj=cmdobj))
            continue_choice = cmdobj.select(enumerate(['Continue', 'Quit'], 1))
            #btc.read_int_ranged('press 1 to continue, 2 to quit: ', 1, 2)
            if continue_choice == 1:
                edit_single_pub(session=session, active_item=active_item, cmdobj=cmdobj)
            elif continue_choice == 2:
                cmdobj.poutput(std('Edit complete, return to main menu', cmdobj=cmdobj))
                break
                #active_item=next(result_cycle)
        except StopIteration:
            cmdobj.poutput('No more publications, return to main menu', cmdobj=cmdobj)
            #print('No more publications, return to main menu')
            return
        #print('Next publication: ', active_item.title)
        #continue_choice = btc.read_int_ranged('press 1 to continue, 2 to quit: ', 1, 2)
        #if continue_choice == 1:
       #     edit_single_pub(session=session, active_item=active_item)
       # elif continue_choice == 2:
        #    break

#Generic EDIT section: these functions relate to editing any item

def edit_name(session, cmdobj, model, id_value, new_name):
    '''Works for: Entry, Category, Section, Keyword, Publication, Author'''
    models = {'entry': Entry, 'category': Category, 'author': Author,
             'section': Section, 'publication': Publication}
    if model in models:
        query = session.query(models.get(model,
            'Please enter "entry", category, section, keyword, publication, author'))
        query = query.filter(models.get(model).id_value == id_value)
        result = query.one()
        confirm_choice = btc.read_int_ranged_adv(f'Replace {result.name_value} with {new_name}? 1-accept, 2-quit: ',
                                                 min_value=1, max_value=2,
                                                 cmdobj=cmdobj, bold=True,
                                                 fg=cmdobj.foreground_color,
                                                 bg=cmdobj.background_color)
        if confirm_choice == 1:
            result.name = new_name
            session.commit()
        else:
            cmdobj.poutput(error_msg('Edit cancelled, return to main menu'))
            #print('edit cancelled, return to main menu')
            return
    else:
        return
    
def edit_second_item(session, model, id_value, new_second_value):
    """Works for Publication, Category"""
    models = {'publication': Publication, 'category': Category, 'roundup':Roundup}
    if model in models:
        query = session.query(models.get(model,
            'Please enter "category", "publication", or "roundup"'))
        query = query.filter(models.get(model).id_value == id_value)
        result = query.first()
        result.second_item = new_second_value
        session.commit()
    else:
        return

def edit_introduction(args, session, cmdobj):
    if args.introduction_id:
        intro = session.query(Introduction).filter(Introduction.id_value == args.introduction_id).first()
        while True:
            cmdobj.poutput(black_white_bg_bold(intro))
            #edit_options_list = [i for i in map(white_darkblue_bg, ['name', 'text', 'exit'])]
            edit_options = cmdobj.select(['name', 'text', 'exit'])
            if edit_options == 'name':
                new_title = btc.read_text_adv(prompt='Enter new name or "." to cancel: ',
                                              cmdobj=cmdobj)
                if new_title != ".":
                    intro.name=new_title
                    session.commit()
                    cmdobj.poutput(std('Introduction name updated', cmdobj=cmdobj))
                    #cmdobj.poutput(black_white_bg_bold('introduction name updated'))
                else:
                    cmdobj.poutput(error_msg('name edit cancelled'))
                    continue
            elif edit_options == 'text':
                new_text = btc.read_text_adv(prompt='Enter new text or "." to cancel: ',
                                             cmdobj=cmdobj)
                if new_text != '.':
                    intro.text=new_text
                    session.commit()
                    cmdobj.poutput(black_white_bg_bold('introduction text updated'))
                else:
                    cmdobj.poutput(error_msg('text edit cancelled'))
                    continue
            elif edit_options == 'exit':
                cmdobj.poutput(black_white_bg_bold('returning to main menu'))
                break
                #still_editing = False

#Edit category section: these functions relate to editing categories

def edit_category(args, session, cmdobj):
    '''while loop displaying the current values for the category,
    options for updating, and lets you display the sections. Takes section_id
    and name as optional arguments as well'''
    query=session.query(Category)
    if args.category_id:
        query=query.filter(Category.id_value == args.category_id)
    elif args.id_range:
        query = query.filter(Category.id_value >= args.id_range[0],
                             Category.id_value <= args.id_range[1])
    elif args.name:
        name_param = ' '.join(args.name)
        query=query.filter(Category.name.like(f"%{name_param}%"))
    elif args.section_id:
        query=query.filter(Category.section_id)
    result = query.all()
    #KEEP EDITING HERE
    result_total = len(result)
    if result_total == 0:
        cmdobj.poutput(error_msg('no categories found'))
        return
    result_cycle = it.cycle(result)
    remaining_cats = len(result)
    cmdobj.poutput(std(f'{remaining_cats} remaining categories', cmdobj=cmdobj))
    while True:
        try:
            active_item=next(result_cycle)
        except StopIteration:
            cmdobj.poutput('No more categories found, return to main menu',
                           bg=cmdobj.background_color,
                           fg=cmdobj.foreground_color)
            return
        cmdobj.poutput(cmd2.style(f'Next category: {active_item.name}',
                            bg=cmdobj.background_color, fg=cmdobj.foreground_color, bold=False))
        continue_choice = cmdobj.select([(1, 'edit'),
                            (2, 'quit to main menu')])
        cat_entry_format = lambda x: cmd2.style(text=x, fg=cmdobj.foreground_color,
                                          bg=cmdobj.background_color, bold=False) #used to format categories and entries
        if continue_choice == 1:
            while True:
                cmdobj.poutput(cmd2.style(text='''\n
{:<20}{:>20}
{:<20}{:>20}
{:<20}{:>20}'''.format('Category ID:', active_item.id_value,
                        'Name:', active_item.name_value,
                        'Section ID:', active_item.section_id),
                    bg=cmdobj.background_color, fg=cmdobj.foreground_color, bold=False))
                edit_choice = cmdobj.select([(1, 'Edit name'), (2, 'Edit section id'),
                                    (3, 'View entries'), (4, 'Next category'),
                                    (5, 'quit')])
                if edit_choice == 1:
                    
                    new_name = btc.read_text_adv('Enter new name or "." to cancel: ',
                                                 cmdobj=cmdobj,
                                                 fg=cmdobj.foreground_color,
                                                 bg=cmdobj.background_color)
                    
                    if new_name != '.':
                        active_item.name = new_name
                        session.commit()
                        cmdobj.poutput(cmd2.style(f'New name is {new_name}',
                                       bg=cmdobj.background_color,
                                       fg=cmdobj.foreground_color))
                    else:
                        cmdobj.poutput(error_msg('Name change cancelled'))
                elif edit_choice == 2:
                    section_list = session.query(Section).all()
                    section_list = [(i.section_id, str(i)) for i in section_list]
                    new_section_id = cmdobj.select(section_list)
                    if new_section_id != 0:
                        cmdobj.poutput(f'Section id changed to: {new_section_id}')
                        edit_second_item(session=session, model='category',
                                         id_value=active_item.id_value,
                                         new_second_value=new_section_id)
                elif edit_choice == 3:
                    view_entries_choice = cmdobj.select([(1, 'view all entries'), (2, 'skip')])
                    #view_entries_choice = btc.read_int_ranged_adv('Type 1 to view all entries for this category, 2 to skip: ',
                    #                                              cmdobj=cmdobj, min_value=1, max_value=2, bold=True)
                    if view_entries_choice == 1:
                        entry_map = map(cat_entry_format, active_item.entries)
                        entry_list = '\n'.join(entry_map)
                        IPython.core.page.page_dumb(entry_list, start=0, screen_lines=25)
                        #cmdobj.poutput(entry_list)
                    else:
                        cmdobj.poutput(error_msg('Entries display cancelled'))
                elif edit_choice == 4:
                    break
                elif edit_choice == 5:
                    raise Exception(error_msg('Edit cancelled, returning to main menu'))
        elif continue_choice == 2:
            break
        
#Edit roundup section:
    
def edit_roundup(args, session, cmdobj):
    '''while loop displaying the current values for the roundup,
    options for updating, and lets you display the sections. Takes section_id
    and name as optional arguments as well'''
    query=session.query(Roundup)
    if args.roundup_id:
        query=query.filter(Roundup.id_value == args.roundup_id)
    if args.title:
        #join the title into a single line
        title = ' '.join(args.title)
        query=query.filter(Roundup.title.like(f'%{title}%'))
    result = query.all()
    #KEEP EDITING HERE
    result_total = len(result)
    if result_total == 0:
        cmdobj.poutput(error_msg('no roundups found'))
        return
    result_cycle = it.cycle(result)
    remaining_rdbs = len(result)
    cmdobj.poutput(black_white_bg_bold(x=f'{remaining_rdbs} remaining roundups'))
    while True:
        try:
            active_item=next(result_cycle)
        except StopIteration:
            cmdobj.poutput(black_white_bg_bold(x='No more roundups found, return to main menu'))
            return
        nextrdb= cmd2.style(text=f'Next roundup: {active_item.title}',
                            bg=cmdobj.background_color, fg=cmdobj.foreground_color, bold=False)
        cmdobj.poutput(nextrdb)
        continue_choice = cmdobj.select([(1, 'continue'), (2, 'quit')])
        if continue_choice == 1:
            while True:
                cmdobj.poutput(black_white_bg(x=f'''\n
Roundup ID: {active_item.id_value}
Name: {active_item.name_value}
Introduction ID: {active_item.introduction_id}
Sections: {active_item.sections}
Start date: {active_item.start_date}
End date: {active_item.end_date}
'''))
                if result_total > 1:
                    edit_choice = cmdobj.select(enumerate(['Edit name', 'Edit introduction ID',
                            'Update entries', 'Update start date', 'Update end date',
                            'Next roundup'], 1))
                    #edit_choice = cmdobj.select([(1, 'Edit name'), (2, 'Edit introduction ID'),
                    #                    (3, 'Update entries'), (4, 'Update dates'), (5, 'Next roundup')])
                elif result_total == 1:
                    edit_choice = cmdobj.select(enumerate(['Edit name', 'Edit introduction ID',
                            'Update entries', 'Update start date', 'Update end date',
                            'Main Menu'], 1))
                if edit_choice == 1:
                    
                    new_name = btc.read_text_adv('Enter new name or "." to cancel: ',
                                        cmdobj=cmdobj, bold=True, bg=cmdobj.background_color,
                                        fg=cmdobj.foreground_color)
                    cmdobj.poutput(std(text=new_name, cmdobj=cmdobj, bold=False))
                    if new_name != '.': 
                        active_item.name_value = new_name
                        session.commit()
                elif edit_choice == 2:
                    intro_list = session.query(Introduction).all()
                    pprint.pprint(intro_list)
                    new_intro_id = btc.read_int_adv('Enter new introduction ID or "0" to cancel: ',
                            cmdobj=cmdobj, bg=cmdobj.background_color, fg=cmdobj.foreground_color)
                    if new_intro_id == 0:
                        cmdobj.poutput(error_msg('Edit cancelled'))
                        break
                    else:
                        edit_second_item(session=session, model='introduction',
                                         id_value=active_item.id_value,
                                         new_second_value=new_intro_id)
                elif edit_choice == 3:
                    update_roundup_articles(session=session, cmdobj=cmdobj,
                                            roundup_id=args.roundup_id)
                elif edit_choice == 4:
                    update_roundup_dates(session=session, cmdobj=cmdobj,
                                            roundup_id = args.roundup_id,
                                            edit_type = 'start date')
                elif edit_choice == 5:
                    update_roundup_dates(session=session, cmdobj=cmdobj,
                                            roundup_id = args.roundup_id,
                                            edit_type = 'end date')
                elif edit_choice == 6:
                    if result_total == 1:
                        raise Exception('No other results found, returning to main menu')
                    elif result_total > 1:
                        break
                #elif edit_choice == 5:
                #    raise Exception(error_msg('Edit cancelled, returning to main menu'))
        elif continue_choice == 2:
            break

def update_roundup_articles(session, cmdobj, roundup_id):
    query = session.query(Roundup)
    query = query.filter(Roundup.id_value == roundup_id).first()
    entries = [i for i in session.query(Entry).filter(Entry.date >= query.start_date,
                                                      Entry.date <= query.end_date)]
    query.entries = entries
    session.commit()
    cmdobj.poutput(black_white_bg_bold(x='Entries update complete'))

def update_roundup_dates(session, cmdobj, roundup_id, edit_type):
    '''Update the dates in the roundup'''
    edit_types = {'start date', 'end date'}
    if edit_type in edit_types:
        query = session.query(Roundup)
        query = query.filter(Roundup.id_value == roundup_id).first()
        cmdobj.poutput(std(query, cmdobj=cmdobj))
        while True:
            edit_options = [(1, 'Edit date'), (2, 'Return to menu')]
            edit_choice = cmdobj.select(edit_options)
            if edit_choice == 1:
                try:
                    new_date = btc.read_date_adv(prompt='Enter new date: ', cmdobj=cmdobj,
                                bold=True)
                except ParserError as e:
                    cmdobj.poutput(error_msg(e))
                #try:
                    #new_date = parse(new_date)
                if edit_type == 'start date':
                    query.start_date = new_date
                        #session.commit()
                        #break
                elif edit_type == 'end date':
                    query.end_date = new_date
                    #session.commit()
                    #break
                session.commit()
                break
                #except ParserError as e:
                #    cmdobj.poutput(error_msg(x=e))
            elif edit_choice == 2:
                cmdobj.poutput('Editing dates complete, returning to main menu')
                break
                

#Edit keyword section: formatting keywords

#Edit publication section: editing publications

#functions that capture input for a publication

#finalize section: functions to finalize articles

#new type of function
#like BTCInput but takes a cmd2obj style as an input
#prints out that style
#then does btc.read_text or read_int or read_int_ranged
#prompt is the prompt for the application

def finalize(session, cmdobj, start_date, end_date):
    start_date = parse(start_date)
    end_date = parse(end_date)
    query = session.query(Entry).filter(Entry.date >= start_date, Entry.date <= end_date)
    query = query.filter(Entry.description.like('%not specified%')).all()
    result = it.cycle(query)
    undescribed_articles = len(query)
    article_count = cmd2.style(text=f'{undescribed_articles} undescribed articles',
                               bg=cmdobj.background_color, fg=cmdobj.foreground_color)
    cmdobj.poutput(article_count)
    while True:
        try:
            active_item=next(result)
        except StopIteration:
            print('No undescribed entries, return to main menu')
            return
        #get the number of undescribed entries
        #print the number of undescribed entries with proper style
        #print article layout
        #take user choice
        undesc = session.query(Entry).filter(Entry.date >= start_date, Entry.date <= end_date)
        undesc = undesc.filter(Entry.description.like('%not specified%')).all()
        undescribed = len(undesc)
        cmdobj.poutput(std(f'{undescribed} undescribed articles remaining', cmdobj=cmdobj))
        #print(f'{undescribed} undescribed articles remaining')
        while True:
            cmdobj.poutput(cmd2.style(text=active_item, bg=cmd2.bg.white,
                fg=cmd2.fg.black, bold=False))
            cmdobj.poutput()
            edit_choices = ['Edit description', 'Edit category id', 'Update keywords', 'Next article',
                            'Quit']
            edit_choice = cmdobj.select(enumerate(edit_choices, 1))
            #edit_choice = cmdobj.select(opts=[(1, 'Edit description'),
            #    (2, 'Edit category id'), (3, 'Next article'), (4, 'Quit')])
            if edit_choice == 1:
                                             
                cmdobj.poutput(black_white_bg_bold('Summary:'))
                cmdobj.poutput(black_white_bg(f'{active_item.summary}'))
                cmdobj.poutput(std(active_item.keywords, cmdobj=cmdobj))
                new_desc = btc.read_text_adv(prompt='Enter new description or "." to cancel, "`" to erase: ',
                                             cmdobj=cmdobj, bold=False,
                                             bg=cmdobj.background_color,
                                             fg=cmdobj.foreground_color)
                if new_desc == '.':
                    cmdobj.poutput(error_msg('edit cancelled'))
                elif new_desc == '`':
                    cmdobj.poutput(error_msg('Description deleted'))
                    active_item.description = 'Not specified'
                    session.commit()
                else:
                    active_item.description = new_desc
                    session.commit()
            elif edit_choice == 2:
                cat_id_finalize(entry_id=active_item.id_value, session=session,
                        cmdobj=cmdobj)
            elif edit_choice == 3:
                update_keywords(session=session, cmdobj=cmdobj, entry_id=active_item.id_value)
            elif edit_choice == 4:
                break
            elif edit_choice == 5:
                raise Exception(error_msg('Return to main menu'))
                    

def set_pubnames(args, session, cmdobj):
    '''When we create new articles, sometimes the publication's metadata
    is not stored properly. This function searches through the publications
    between two publication_id values and lets the user enter the titles
    correctly'''
    if args.id_range:
        minimum_id = args.id_range[0]
        maximum_id = args.id_range[1]
        result = session.query(Publication).filter(Publication.id_value >= minimum_id, 
                                  Publication.id_value <= maximum_id).all()
        results = it.cycle([i for i in result if i.url == i.name_value])
        while True:
            new_pub = next(results)
            cmdobj.poutput(cmd2.style(text=new_pub,
                    bg=cmdobj.background_color, fg=cmdobj.foreground_color))
            edit_opts = [f'Edit {new_pub.title}', 'Continue', 'Quit']
            edit_choice = cmdobj.select(enumerate(edit_opts, 1))
            #edit_choice = cmdobj.select([(1, f'edit {new_pub.title}'), (2, 'continue'), (3, 'quit')])
            #edit_choice = btc.read_int_ranged(f'Type 1 to edit {new_pub.title}, 2 to continue, 3 to quit: ', 1, 3)
            if edit_choice == 1:
                new_title = btc.read_text_adv('Enter new title or "." to cancel: ',
                    cmdobj=cmdobj)
                if new_title != ".":
                    new_pub.title = new_title
                    session.commit()
                else:
                    cmdobj.poutput(std('Edit cancelled', cmdobj=cmdobj))
                    #print('Edit cancelled')
            elif edit_choice == 3:
                cmdobj.poutput(std('Edit cancelled', cmdobj=cmdobj))
                #print('Edit cancelled')
                break
                
def merge_pub(args, session):
    #args contains: url
    #get all publication urls:
    query_one = session.query(Publication).all()
    if args.id_range:
        query_one = query_one.filter(Publication.id_value >= args.id_range[0],
                                     Publication.id_value <= args.id_range[1])
    duplicate_counter = Counter([i.url for i in query_one])
    for i in duplicate_counter.items():
        print(i)

#Edit entry section: these functions relate to editing entries

#These functions seem repetitive, let's consolidate them onto fewer lines of code

def name_from_input(session, cmdobj, entry_id):
    '''Gets user input for the article name, the name editing itself is carried out by the edit_name function'''
    query = session.query(Entry)
    query = query.filter(Entry.entry_id == entry_id)
    result = query.one()
    cmdobj.poutput(black_white_bg(result))
    cmdobj.poutput() #blank line for space
    edit_choice = cmdobj.select(opts=enumerate(['Yes', 'No'], 1))
    if edit_choice == 1:
        new_name = btc.read_text_adv('Enter new name (i.e. title) or "." to cancel: ',
                                     cmdobj=cmdobj, fg=cmdobj.foreground_color,
                                     bg=cmdobj.background_color,
                                     bold=False)
        if new_name != '.':
            edit_name(session=session, cmdobj=cmdobj, model='entry', id_value = entry_id, new_name=new_name)
        else:
            cmdobj.poutput(error_msg('Edit name cancelled'))
            return
    elif edit_choice == 2:
        cmdobj.poutput(error_msg('Edit entry cancelled'))
        return
    
def edit_date(session, cmdobj, entry_id, new_date):
    '''Takes a date from "date_from_input" below and adds it to the database'''
    query = session.query(Entry)
    query = query.filter(Entry.entry_id == entry_id)
    result = query.one()
    result.date = new_date
    session.commit()
    cmdobj.poutput(std(new_date, cmdobj=cmdobj, bold=False))
    cmdobj.poutput(black_white_bg_bold('Entry edit successful'))
    
def date_from_input(session, cmdobj, entry_id):
    '''Takes user input of the text of a date and converts it to a date object.
    Then, the date object is used to update the entry.
    params:
    :session: the session object from ui.py
    :cmdobj: the cmd2.Cmd instance running in ui.py
    :entry_id: the entry of the article being edited'''
    query = session.query(Entry)
    query = query.filter(Entry.entry_id == entry_id)
    result = query.one()
    cmdobj.poutput(result)
    edit_choice = cmdobj.select(enumerate(['Yes', 'No'], 1))
    #edit_choice = cmdobj.select(opts=[(1, 'yes'), (2, 'no')])
    #edit_choice = btc.read_int_ranged('Edit date (1 for yes, 2 for no): ', 1, 2)
    if edit_choice == 1:
        new_date = btc.read_text('Enter new date or "." to cancel: ')
        new_date = parse(new_date)
        if new_date != '.':
            edit_date(session=session, cmdobj=cmdobj, entry_id=entry_id, new_date=new_date)
        else:
            cmdobj.poutput(std('Edit date cancelled', cmdobj=cmdobj))
            #print('Edit date cancelled')
            return
    if edit_choice == 2:
        cmdobj.poutput(std('Edit cancelled', cmdobj=cmdobj))
        #print('Edit cancelled')
        return
    
def edit_description(session, cmdobj, entry_id, new_description):
    query = session.query(Entry)
    query = query.filter(Entry.entry_id == entry_id)
    result = query.one()
    result.description = new_description
    session.commit()
    cmdobj.poutput(std('Entry edit successful', cmdobj=cmdobj))
    
def desc_from_input(session, cmdobj, entry_id):
    query = session.query(Entry)
    query = query.filter(Entry.entry_id == entry_id)
    result = query.one()
    cmdobj.poutput(std(result, cmdobj=cmdobj, bold=False))
    cmdobj.poutput()
    edit_choice = cmdobj.select(enumerate(['Yes', 'No'], 1),
                    prompt='Edit description?')
    #edit_choice = cmdobj.select(opts=[(1, 'yes'), (2, 'no')],
    #                            prompt='Edit description?')
    if edit_choice == 1:
        cmdobj.poutput(cmd2.style(result.summary, bg=cmdobj.background_color,
            fg=cmdobj.foreground_color, bold=False))
        new_description = btc.read_text_adv('Enter new description or "." to cancel: ',
                                                    cmdobj=cmdobj)
        if new_description != '.':
            edit_description(session=session, cmdobj=cmdobj,
                entry_id=entry_id, new_description=new_description)
        else:
            cmdobj.poutput(error_msg('Edit description cancelled'))
            return
    if edit_choice == 2:
        cmdobj.poutput(error_msg('Edit cancelled'))
        return

def cat_id_finalize(session, cmdobj, entry_id):
    display_categories(cmdobj=cmdobj, section_id=None)
    new_category_id = btc.read_int_adv('Enter new category id or 0 to cancel: ',
                            cmdobj=cmdobj)
    if new_category_id == 0:
        cmdobj.poutput(error_msg('Edit category ID cancelled'))
        #print('edit category id cancelled')
    else:
        query = session.query(Entry)
        query = query.filter(Entry.entry_id == entry_id)
        result = query.one()
        result.category_id = new_category_id
        session.commit()
        cmdobj.poutput(std('Entry edit successful', cmdobj=cmdobj))
        #print('Entry edit successful')    
    
def edit_category_id(session, cmdobj, entry_id, new_category_id):
    query = session.query(Entry)
    query = query.filter(Entry.entry_id == entry_id)
    result = query.one()
    result.category_id = new_category_id
    session.commit()
    cmdobj.poutput(std('Category ID edit successful', cmdobj=cmdobj))
    #print('Entry edit successful')
    
def cat_id_from_input(session, cmdobj, entry_id):
    query = session.query(Entry)
    query = query.filter(Entry.entry_id==entry_id)
    result = query.one()
    #print(result)
    cmdobj.poutput(std(result, cmdobj=cmdobj))
    edit_opts = ['Edit category id', 'Cancel']
    edit_choice = cmdobj.select(opts=enumerate(edit_opts, 1))
    #edit_choice=btc.read_int_ranged('Edit category ID (1 for yes, 2 for no): ', 1, 2)
    if edit_choice == 1:
        display_categories(cmdobj=cmdobj, section_id = None)
        new_category_id = btc.read_int_adv('Enter category id or 0 to cancel: ',
                                        cmdobj=cmdobj)
        if new_category_id <= 0:
            cmdobj.poutput(std('Edit category ID cancelled, return to main menu',
                                cmdobj=cmdobj))
            #print('Edit category ID cancelled, return to main menu')
            return
        else:
            edit_category_id(session=session, cmdobj=cmdobj, entry_id=entry_id,
                             new_category_id=new_category_id)
            
        
def edit_entry(session, entry_id, cmdobj):
    entry = get(session=session, model=Entry, entry_id=entry_id)
    choices = {1: name_from_input, 2: date_from_input,
               3: cat_id_from_input, 4: desc_from_input}
    while True:
       # e_style = cmd2.style(entry, fg=cmdobj.foreground_color, bg=cmdobj.background_color, bold=False)
        cmdobj.poutput(std(entry, cmdobj=cmdobj, bold=False))
        edit_opts = ['Edit name', 'Edit date', 'Edit category id', 'Edit description',
        'Finish editing']
        choice = cmdobj.select(enumerate(edit_opts, 1))
        if choice <= 4:
            choices.get(choice)(session=session, entry_id=entry_id,
                                cmdobj=cmdobj)
        elif choice == 5:
            editing_complete = cmd2.style('Editing complete', bg=cmd2.bg.red,
                                          fg=cmd2.fg.white, bold=True)
            cmdobj.poutput(editing_complete)
            break
        
#create section - functions for creating new instances

#add_articles: this section is for adding entries, this is separate due to the complexity of the code. The entries
#must be downloaded using the newspaper app.

def add_intro(session, cmdobj, name, text):
    '''Add introduction to database from a user command'''
    new_intro = Introduction(name=name, text=text)
    session.add(new_intro)
    session.commit()
    add_complete_intro = cmd2.style(text=f'{new_intro}')
    cmdobj.poutput(add_complete_intro)

def create_entry(article, description, publication_id, category_id, date, authors=[],
                 keywords=[]):
    return Entry(entry_name=article.title, entry_url=article.url,
            description=description, summary=article.summary,
            authors=authors, publication_id=publication_id,
        category_id=category_id, keywords=keywords, date=date)

def add_entry_two(session, cmdobj, url, category_id, date, manual_description='no', description='Not specified', category_name=None,
              new_keywords=None):
    'qa is short for quick_add'
    try:
        assert len(url) > 10, 'url out of order'
    
    except AssertionError as e:
        #one of the parameters is entered incorrectly
        print(e)
        return
    new_article = make_article(url)
    cmdobj.poutput(cmd2.style('\nTitle is being added...\n', fg=cmdobj.foreground_color,
                   bg=cmdobj.background_color, bold=True))
    cmdobj.poutput(std(text=new_article.title, cmdobj=cmdobj,
                       bold=False))
    new_pub = get(session, Publication, url=new_article.source_url)
    if new_pub == None:
        new_pub = get_or_create(session, Publication,
                        title=new_article.source_url,
                        url=new_article.source_url)
        cmdobj.poutput(cmd2.style(text=new_pub, bg=cmdobj.background_color,
            fg=cmdobj.background_color))
        #cmdobj.poutput(new_pub_notice)
    if type(date) == str:
        #If it is a string then it can be parsed by parse()
        date=parse(date) #this will raise an exception if it is not a date
    if description == 'Not specified':
        if manual_description == 'yes':
            cmdobj.poutput(cmd2.style(text=new_article.title, fg=cmdobj.foreground_color,
                                     bg=cmdobj.background_color, bold=True))
            cmdobj.poutput(cmd2.style(text=new_article.summary, fg=cmdobj.foreground_color,
                                     bg=cmdobj.background_color, bold=False))
            description_prompt = btc.read_text_adv(prompt='Enter article description or "." to cancel: ',
                                                   cmdobj=cmdobj,
                                                   bg=cmdobj.background_color,
                                                   fg=cmdobj.foreground_color)
            if description_prompt == '.':
                description='Not specified'
            else:
                description = description_prompt
        elif manual_description=='no':
            description='Not specified'
    if new_keywords:
        for i in new_keywords:
            choice = btc.read_int_ranged(f'add {i} to keywords?', 1, 2)
            if choice == 1:
                new_article.keywords.append(i)
                cmdobj.poutout(f'{i} added to keywords manually')
    authors = [get_or_create(session, Author, author_name=i) for i in new_article.authors]
    keywords = [get_or_create(session, Keyword, word=i) for i in new_article.keywords]
    new_entry= create_entry(article=new_article, description=description,
                            publication_id=new_pub.publication_id, category_id=category_id,
                            date=date, authors=authors, keywords=keywords)
    session.add(new_entry)
    session.commit()
    cmdobj.poutput(black_white_bg(str(new_entry)))
    cmdobj.poutput(black_white_bg_bold(x='Entry added successfully'))

# --------------------- NEW ADD ENTRY FUNCTIONS --------- 14 July 2020 ---------------

#add multiple entries from google search
def add_articles_from_search(session, args, cmdobj):
    '''Add articles from google search
    params:
        session: session object
        args: argparse namespace object
        cmdobj: 
    
    '''
    googlenews = GoogleNews(start=args.start_date, end=args.end_date)
    googlenews.search(args.keyword)
    googlenews.getpage(int(args.num_pages))
    articles = [i for i in googlenews.result()]
    for article in articles:
        cmdobj.poutput(std(article, cmdobj=cmdobj))
        article_choice = cmdobj.select([(1, 'Add article'), (2,'Skip article'),
                    (3, 'Quit to main menu ')])
        if article_choice == 1:
            try:
                article['date'] = parse(article['date']).date()
                add_from_search_two(session=session, cmdobj=cmdobj, url=article['link'], date=article['date'])
            except ParserError:
                add_from_search_two(session=session, cmdobj=cmdobj, url=article['link'], date=None)
        elif article_choice == 3:
            cmdobj.poutput(error_msg('Returning to main menu'))
            break
    return

#ADD INDIVIDUAL ARTICLES FROM SEARCH
#NEW METHOD OF GENERATING VOCABULARY
def add_from_search_two(session, cmdobj, url, date=None):
    '''Add an individual article from a google search'''
    args_dict = {'entry_url': url}
    if date != None:
        cmdobj.poutput(error_msg(date))
        args_dict['date'] = date
    print(args_dict)
    #raise NotImplementedError
    nlp = spacy.load('en_core_web_sm')
    print('URL:', args_dict['entry_url'])
    new_entry = Article(args_dict['entry_url'])
    new_entry.build()
    #print(new_entry)
    args_dict['entry_name'] = new_entry.title
    #args_dict = {'entry_url':args.url,
    #            'entry_name': new_entry.title}
    args_dict['description'] = 'Not specified'
    #if args.description == None:
    #    args_dict['description'] = 'Not specified'
    #else:
    #    args_dict['description'] = ' '.join(args.description)
    #    print('Description: ', args.description)
    #take the doc and get the article title, add it to the dictionary
    cmdobj.poutput(error_msg('Arguments so far: '))
    cmdobj.poutput(std(args_dict, cmdobj=cmdobj))
    print(args_dict)
    #get the date
    #if args.custom_date == None:
    #    cmdobj.poutput(error_msg('Custom date not found'))
        #if the user does not enter a custom date, we don't need to find it
    args_dict['date'] = get_date_from_article(new_entry, cmdobj)
    #elif args.custom_date != None:
    #get the authors
    art_authors = authors_from_np(session=session, article=new_entry, nlp=nlp)
    print(art_authors)
    #make sure we don't grab the wrong people as the authors
    for author in art_authors:
        print('Author:', author)
        print(len(author.author_name))
        if len(author.author_name) == 1: #if its captured the names wrong
            art_authors.remove(author)
            #args_dict['authors'].pop(author) #if it's read wrong
        args_dict['authors'] = art_authors
    try:
        print(args_dict['authors'])
    except KeyError:
        cmdobj.poutput(std('No authors found', cmdobj=cmdobj))
        args_dict['authors'] = []
    #get the publication
    pub = get_publication_from_article(session=session, article=new_entry)
    args_dict['publication_id'] = pub.publication_id
    #get the category
    #make sure we have not already specified the category
    #try:
        #assert args.custom_category == None, 'Category specified by user'
    cat_choices = get_categories_from_article(session=session, article=new_entry, nlp=nlp)
    if len(cat_choices) == 1:
        args_dict['category_id'] = cat_choices[0].category_id
    elif len(cat_choices) > 1:
        new_cats = [(i.category_id, str(i)) for i in cat_choices]
        args_dict['category_id'] = cmdobj.select(prompt='Enter category ID: ',
            opts = new_cats)
    #except AssertionError:
    #    cmdobj.poutput(error_msg('Category specified by user'))
    #    args_dict['category_id'] = args.custom_categories

    #GET ENTITY WORDS
    doc=nlp(new_entry.text)
    permitted_labels = {'PERSON', 'LOC', 'GPE', 'ORG', 'PRODUCT', 'EVENT'}
    for i in doc.ents:
        print(error_msg(i))
    new_keywords = list({i.text for i in doc.ents if i.label_ in permitted_labels})
    args_dict['keywords'] = [get_or_create(session=session, model=Keyword,
                                          word=i) for i in new_keywords]

    #args_dict['keywords'] = 

   # args_dict['keywords'] = [get_or_create(session=session, model=Keyword,
    #                                      word=i) for i in new_entry.keywords]
    args_dict['summary'] = new_entry.summary
    print(args_dict)
    try:
        entry_to_add = Entry(**args_dict)
    except TypeError:
        cats = [(i.category_id, str(i)) for i in session.query(Category).all()]
        args_dict['category_id'] = cmdobj.select(cats)
        entry_to_add = Entry(**args_dict)
    except IntegrityError:
        session.rollback()
        args_dict['authors'] = []
        entry_to_add = Entry(**args_dict)
    print(entry_to_add.entry_name)
    try:
        session.add(entry_to_add)
        session.commit()
    except IntegrityError:
        session.rollback()
        cmdobj.poutput(error_msg('Add method 1 failed, retrying...'))
        args_dict['authors'] = []
        entry_to_add = Entry(**args_dict)
        session.add(entry_to_add)
        session.commit()
    cmdobj.poutput(entry_to_add)

#ADD INDIVIDUAL ARTICLE FROM GOOGLE SEARCH
def add_from_search(session, cmdobj, url, date=None):
    '''Add an individual article from a google search'''
    args_dict = {'entry_url': url}
    if date != None:
        cmdobj.poutput(error_msg(date))
        args_dict['date'] = date
    print(args_dict)
    #raise NotImplementedError
    nlp = spacy.load('en_core_web_sm')
    print('URL:', args_dict['entry_url'])
    new_entry = Article(args_dict['entry_url'])
    new_entry.build()
    #print(new_entry)
    args_dict['entry_name'] = new_entry.title
    #args_dict = {'entry_url':args.url,
    #            'entry_name': new_entry.title}
    args_dict['description'] = 'Not specified'
    #if args.description == None:
    #    args_dict['description'] = 'Not specified'
    #else:
    #    args_dict['description'] = ' '.join(args.description)
    #    print('Description: ', args.description)
    #take the doc and get the article title, add it to the dictionary
    cmdobj.poutput(error_msg('Arguments so far: '))
    cmdobj.poutput(std(args_dict, cmdobj=cmdobj))
    print(args_dict)
    #get the date
    #if args.custom_date == None:
    #    cmdobj.poutput(error_msg('Custom date not found'))
        #if the user does not enter a custom date, we don't need to find it
    args_dict['date'] = get_date_from_article(new_entry, cmdobj)
    #elif args.custom_date != None:
    #get the authors
    art_authors = authors_from_np(session=session, article=new_entry, nlp=nlp)
    print(art_authors)
    #make sure we don't grab the wrong people as the authors
    for author in art_authors:
        print('Author:', author)
        print(len(author.author_name))
        if len(author.author_name) == 1: #if its captured the names wrong
            art_authors.remove(author)
            #args_dict['authors'].pop(author) #if it's read wrong
        args_dict['authors'] = art_authors
    try:
        print(args_dict['authors'])
    except KeyError:
        cmdobj.poutput(std('No authors found', cmdobj=cmdobj))
        args_dict['authors'] = []
    #get the publication
    pub = get_publication_from_article(session=session, article=new_entry)
    args_dict['publication_id'] = pub.publication_id
    #get the category
    #make sure we have not already specified the category
    #try:
        #assert args.custom_category == None, 'Category specified by user'
    cat_choices = get_categories_from_article(session=session, article=new_entry, nlp=nlp)
    if len(cat_choices) == 1:
        args_dict['category_id'] = cat_choices[0].category_id
    elif len(cat_choices) > 1:
        new_cats = [(i.category_id, str(i)) for i in cat_choices]
        args_dict['category_id'] = cmdobj.select(prompt='Enter category ID: ',
            opts = new_cats)
    #except AssertionError:
    #    cmdobj.poutput(error_msg('Category specified by user'))
    #    args_dict['category_id'] = args.custom_categories

    args_dict['keywords'] = [get_or_create(session=session, model=Keyword,
                                          word=i) for i in new_entry.keywords]
    args_dict['summary'] = new_entry.summary
    print(args_dict)
    try:
        entry_to_add = Entry(**args_dict)
    except TypeError:
        cats = [(i.category_id, str(i)) for i in session.query(Category).all()]
        args_dict['category_id'] = cmdobj.select(cats)
        entry_to_add = Entry(**args_dict)
    except IntegrityError:
        session.rollback()
        args_dict['authors'] = []
        entry_to_add = Entry(**args_dict)
    print(entry_to_add.entry_name)
    try:
        session.add(entry_to_add)
        session.commit()
    except IntegrityError:
        session.rollback()
        cmdobj.poutput(error_msg('Add method 1 failed, retrying...'))
        args_dict['authors'] = []
        entry_to_add = Entry(**args_dict)
        session.add(entry_to_add)
        session.commit()
    cmdobj.poutput(entry_to_add)

#add multiple entries
def add_articles_to_database(session, args, cmdobj):
    nlp = spacy.load('en_core_web_sm')
    for url in args.urls:
        print('URL:', url)
        new_entry = Article(url)
        new_entry.build()
        #print(new_entry)
        args_dict = {'entry_url':url,
                    'entry_name': new_entry.title,
                    'description': 'Not specified'}
        #we cannot set descriptions in this command
        #if args.description == None:
        #    args_dict['description'] = 'Not specified'
        #else:
        #    args_dict['description'] = ' '.join(args.description)
        #    print('Description: ', args.description)
        #take the doc and get the article title, add it to the dictionary
        cmdobj.poutput(error_msg('Arguments so far: '))
        cmdobj.poutput(std(args_dict, cmdobj=cmdobj))
        print(args_dict)
        #get the date
        args_dict['date'] = get_date_from_article(new_entry, cmdobj,
                                    custom_date_range=args.custom_date_range)
        #get the authors
        art_authors = authors_from_np(session=session, article=new_entry, nlp=nlp)
        #make sure we don't grab the wrong people as the authors
        for author in art_authors:
            print('Author:', author)
            print(len(author.author_name))
            if len(author.author_name) == 1: #if its captured the names wrong
                art_authors.remove(author)
                #args_dict['authors'].pop(author) #if it's read wrong
            args_dict['authors'] = art_authors
        try:
            print(args_dict['authors'])
        except KeyError:
            cmdobj.poutput(std('No authors found', cmdobj=cmdobj))
            args_dict['authors'] = []
        #print(args_dict['authors'])
        #get the publication
        pub = get_publication_from_article(session=session, article=new_entry)
        args_dict['publication_id'] = pub.publication_id
        #get the category
        cat_choices = get_categories_from_article(session=session, article=new_entry, nlp=nlp)
        if len(cat_choices) == 1:
            args_dict['category_id'] = cat_choices[0].category_id
        elif len(cat_choices) > 1:
            new_cats = [(i.category_id, str(i)) for i in cat_choices]
            args_dict['category_id'] = cmdobj.select(prompt='Enter category ID: ',
                opts = new_cats)
        args_dict['keywords'] = [get_or_create(session=session, model=Keyword,
                                                word=i) for i in new_entry.keywords]
        args_dict['summary'] = new_entry.summary
        print(args_dict)
        try:
            entry_to_add = Entry(**args_dict)
        except TypeError:
            cats = [(i.category_id, str(i)) for i in session.query(Category).all()]
            args_dict['category_id'] = cmdobj.select(cats)
            entry_to_add = Entry(**args_dict)
        except IntegrityError:
            session.rollback()
            args_dict['authors'] = []
            entry_to_add = Entry(**args_dict)
        print(entry_to_add.entry_name)
        try:
            session.add(entry_to_add)
            session.commit()
        except IntegrityError:
            session.rollback()
            cmdobj.poutput(error_msg('Add method 1 failed, retrying...'))
            args_dict['authors'] = []
            entry_to_add = Entry(**args_dict)
            session.add(entry_to_add)
            session.commit()
        cmdobj.poutput(entry_to_add)

#add single entry
def add_article_to_database(session, args, cmdobj):
    '''Adds an article from a url to the database
    params:
        session: the session object
        url: the url of the article
        '''
    nlp = spacy.load('en_core_web_sm')
    print('URL:', args.url)
    new_entry = Article(args.url)
    new_entry.build()
    #print(new_entry)
    args_dict = {'entry_url':args.url,
                'entry_name': new_entry.title}
    if args.description == None:
        args_dict['description'] = 'Not specified'
    else:
        args_dict['description'] = ' '.join(args.description)
        print('Description: ', args.description)
    #take the doc and get the article title, add it to the dictionary
    cmdobj.poutput(error_msg('Arguments so far: '))
    cmdobj.poutput(std(args_dict, cmdobj=cmdobj))
    print(args_dict)
    #get the date
    if args.custom_date == None:
        cmdobj.poutput(error_msg('Custom date not found'))
        #if the user does not enter a custom date, we don't need to find it
        args_dict['date'] = get_date_from_article(new_entry, cmdobj)
    elif args.custom_date != None:
        cmdobj.poutput(error_msg('Custom date found'))
        cmdobj.poutput(error_msg(args.custom_date))
        try:
            #make sure the custom date is valid
            args_dict['date'] = parse(args.custom_date)
        except Exception as e:
            #if the date the user enters was wrong
            cmdobj.poutput(error_msg(f'{e}. Attempting to find date'))
            args_dict['date'] = get_date_from_article(new_entry, cmdobj)
    #get the authors
    art_authors = authors_from_np(session=session, article=new_entry, nlp=nlp)
    print(art_authors)
    #make sure we don't grab the wrong people as the authors
    for author in art_authors:
        print('Author:', author)
        print(len(author.author_name))
        if len(author.author_name) == 1: #if its captured the names wrong
            art_authors.remove(author)
            #args_dict['authors'].pop(author) #if it's read wrong
        args_dict['authors'] = art_authors
    try:
        print(args_dict['authors'])
    except KeyError:
        cmdobj.poutput(std('No authors found', cmdobj=cmdobj))
        args_dict['authors'] = []
    #get the publication
    pub = get_publication_from_article(session=session, article=new_entry)
    args_dict['publication_id'] = pub.publication_id
    #get the category
    #make sure we have not already specified the category
    try:
        assert args.custom_category == None, 'Category specified by user'
        cat_choices = get_categories_from_article(session=session, article=new_entry, nlp=nlp)
        if len(cat_choices) == 1:
            args_dict['category_id'] = cat_choices[0].category_id
        elif len(cat_choices) > 1:
            new_cats = [(i.category_id, str(i)) for i in cat_choices]
            args_dict['category_id'] = cmdobj.select(prompt='Enter category ID: ',
                opts = new_cats)
    except AssertionError:
        cmdobj.poutput(error_msg('Category specified by user'))
        args_dict['category_id'] = args.custom_category
    args_dict['keywords'] = [get_or_create(session=session, model=Keyword,
                                          word=i) for i in new_entry.keywords]
    args_dict['summary'] = new_entry.summary
    print(args_dict)
    try:
        entry_to_add = Entry(**args_dict)
    except TypeError:
        cats = [(i.category_id, str(i)) for i in session.query(Category).all()]
        args_dict['category_id'] = cmdobj.select(cats)
        entry_to_add = Entry(**args_dict)
    except IntegrityError:
        session.rollback()
        args_dict['authors'] = []
        entry_to_add = Entry(**args_dict)
    print(entry_to_add.entry_name)
    try:
        session.add(entry_to_add)
        session.commit()
    except IntegrityError:
        session.rollback()
        cmdobj.poutput(error_msg('Add method 1 failed, retrying...'))
        args_dict['authors'] = []
        entry_to_add = Entry(**args_dict)
        session.add(entry_to_add)
        session.commit()
    cmdobj.poutput(entry_to_add)
    #return entry_to_add

#Category Info -------

def get_categories_from_article(session, article, nlp):
    #use this to get the category for the article
    '''Takes an Article object from the newspaper module and returns its category'''
    text=article.text
    cat_result = get_categories_from_text(session=session, text=text, nlp=nlp)
    categories = [session.query(Category).filter(Category.name == i).first() for i in cat_result]
    return categories

def get_categories_from_text(session, text, nlp):
    #pipeline function one
    '''Takes a session, text, and nlp and returns a list of category names present in the document'''
    places = set(get_places_from_text(session=session, text=text, nlp=nlp))
    #print(places)
    cat_names = {i.name for i in session.query(Category).all()}
    #cat_names = set(get_category_names(session))
    return list(cat_names.intersection(places))
    #print(cat_names)
    
def get_places_from_text(session, text, nlp):
    #pipeline function two
    '''Takes a text and gets the entities from it
    converts them into text form and returns
    a list'''
    doc=nlp(text)
    places = []
    for ent in doc.ents:
        if ent.root.ent_type_ == 'GPE':
            places.append(str(ent))
    return places

#def get_category_names(session):
#    #pipeline function three
#    '''Gets the category names rather than the categories'''
#    return {i.name for i in session.query(Category).all()}

#Date Info ------

###get date from article
def get_date_from_article(article, cmdobj, custom_date_range=None):
    #date pipeline item 1
    '''Takes an article and gets the likely publication from it
    params:
        article: the article that is being searched for the date
        cmdobj: the cmd2.Cmd object from the main application (ui.py)
        '''
    try:
        new_date = get_date_from_metadata(article)
        assert new_date != None, 'date not found in metadata'
        print('Date found in metadata:', new_date)
    except AssertionError as e:
        print(e) #print the error test
        new_date = get_date_from_regex(article.url) #get the date from the regex in the url if we can
    try:
        assert new_date != None, 'date not found in url'
    except AssertionError as e:
        new_date = get_date_from_input(cmdobj=cmdobj,
                    custom_date_range=custom_date_range)
    return new_date

def get_date_from_metadata(article):
    #date pipeline item 2: check first to see if the date is in the article's metadata
    '''gets the date from the article's metadata'''
    try:
        return article.publish_date.date()
    except AttributeError:
        return None
    #pass

def get_date_regex_from_url(url):
    #date pipeline item 4
    '''Takes a url and gets the likely date from it'''
    date_result = re.findall(r'/(\d{4})/(\d{1,2})/(\d{1,2})/', url)
    
    return date_result

def get_date_from_regex(url):
    #date pipeline item 3
    try:
        regex_tuple = get_date_regex_from_url(url=url)
        return parse('-'.join(regex_tuple[0])).date()
    except Exception as e:
        print(e)
        return None

def get_date_from_text(text):
    #date item pipeline 5
    '''Takes a text and gets the likely date from it'''
    pass

def get_date_from_input(cmdobj, custom_date_range=None):
    '''Gets the date from the user if it cannot be found in the document
    params:
        cmdobj: the cmd2.Cmd object from the main application
    returns:
        date_selected: the date the user has selected
    '''
    while True:
        try:
            if custom_date_range != None:
                try:
                    assert len(custom_date_range) == 2, 'Custom date range must have two dates'
                    start_date = parse(custom_date_range[0])
                    end_date = parse(custom_date_range[1])
                    date_range = range_from_dates(start_date, end_date)
                except AssertionError: #if there's not two dates
                    date_range = range_from_dates(cmdobj.start_date,
                                                cmdobj.end_date)
            else:
                date_range = range_from_dates(cmdobj.start_date,
                                        cmdobj.end_date)
            date_choices = [(i, i.strftime("%B %d, %Y (%A)")) for i in date_range]
            date_selected = cmdobj.select(date_choices)
            break
        except Exception as e:
            print(e)
            continue
    return date_selected

#Publication Info ------

def get_publication_from_article(session, article):
    #publication pipeline stage 1
    ''''''
    try:
        pub = get_publication_from_metadata(session=session, article=article)
        assert pub != None
        return pub
    except AssertionError:
        print('Publication not found')
        pub = get_or_create(session=session, model=Publication,
                           url=article.source_url, title=article.source_url)
        return pub

def get_publication_from_metadata(session, article):
    #publication pipeline stage 2
    '''Takes a text and gets the likely publication from the article metadata
    
    params:
        session: DataAccessLayer.session
        article: newspaper.Article
        
    returns:
        publication if found in the text'''
    
    #source_url = art.source_url
    pub = session.query(Publication).filter(Publication.url == article.source_url).first()
    return pub

#Author Info-------

def authors_from_np(session, article, nlp):
    '''Takes an Article object and gets the authors from it.'''
    authors = get_authors_from_article(session=session, article=article, nlp=nlp)
    try:
        new_authors = [get_or_create(session=session, model=Author, author_name=i) for i in authors]
    except Exception as e:
        print(e)
        new_authors = []
    return new_authors

def get_authors_from_article(session, article, nlp):#, nlp):
    '''Takes an article object and returns the authors of that article'''
    #nlp=spacy.load('en')
    try:
        authors=get_authors_from_metadata(session=session, article=article)
        assert len(authors) > 0
        return authors
    except AssertionError:
        #doc=nlp(article.text)
        authors = []
        #authors = get_author_from_text(session=session, doc=nlp(article.text), nlp=nlp)#, nlp=nlp)
        return authors

def get_authors_from_metadata(session, article):
    return article.authors

# def get_author_from_text(session, doc, nlp):
#     '''Get the author directly from the text, authors tend to be in the beginning.
#     At this point this only works with one author.'''
    
#     adp_plus = []
#     doc_index = 0
#     for j, token in enumerate(doc[:10]):
#         print(token)
#         print(token.text)
#         print(token.ent_type)
#         if token.text.lower() == 'by':
#             doc_index = j
#     for token in doc[doc_index:10]:
#         if token.pos_ == 'PROPN':
#             print(token.text, token.ent_type)
#             adp_plus.append(token)
#     author_name = ' '.join([i.text for i in adp_plus])
#     return author_name

#END OF NEW ADD FUNCTION

#delete section - delete article

def delete_item(session, cmdobj, model, id_value):
    model = model.lower()
    models = {'entry': Entry, 'category': Category, 'keyword': Keyword,
             'author': Author, 'publication': Publication, 'section': Section,
             'introduction': Introduction, 'roundup': Roundup}
    result = get(session=session, model = models.get(model, 'invalid delete type'),
                id_value=id_value)
    if result != None:
        result_style = cmd2.style(text=result, fg=cmdobj.foreground_color,
                                  bg=cmdobj.background_color,
                                  bold=False)
        cmdobj.poutput(result_style)
        delete_choice = btc.read_int_ranged_adv(f'Delete {model} (1 for yes, 2 for no)?',
                                                min_value=1, max_value=2,
                                                fg=cmd2.fg.yellow,
                                                bg=cmd2.bg.red,
                                                bold=True,
                                                cmdobj=cmdobj)         
        if delete_choice == 1:
            if (model == 'category') or (model=='section') or (model=='publication'):
                try:
                    assert len(result.items) == 0
                except AssertionError:
                    cmdobj.poutput(error_msg('Result has items, delete these first'))
                    cmdobj.poutput(result.items)
                    return
            confirm_choice = btc.read_int_ranged_adv('Are you sure (1 for yes, 2 for no)?',
                                                     min_value=1, max_value=2,
                                                     fg=cmd2.fg.yellow,
                                                     bg=cmd2.bg.red,
                                                     bold=True,cmdobj=cmdobj)
            if confirm_choice == 1:
                #delete the article
                session.delete(result)
                session.commit()
                cmdobj.poutput(error_msg(f'{result_style} deleted'))
            elif confirm_choice == 2:
                remains_message = cmd2.style('f{result_style} remains in database',
                                             fg=cmd2.fg.yellow,
                                             bg=cmd2.bg.red,
                                             bold=False)
                cmdobj.poutput(error_msg('Delete cancelled'))
                cmdobj.poutput(remains_message)
        else:
            cmdobj.poutput(error_msg('Delete cancelled by user, returning to main menu'))
    else:
        cmdobj.poutput(error_msg('Item not found, delete cancelled'))
    
dal = DataAccessLayer()

class App:
    def __init__(self):
        self.d = dal
    
    def setup(self):
        self.d.conn_string = 'sqlite:///roundup_db3.db'
        self.d.connect()
        self.d.session = dal.Session()
    def close(self):
        self.d.session.close()

if __name__ == '__main__':
    pass

#1410 lines - 05/18/2020
#1572 LINES - 05/17/2020