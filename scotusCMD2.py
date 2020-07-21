#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  4 07:46:04 2020

@author: thomassullivan
"""

import os
import argparse
import pprint
import re
import sys
import datetime
import json
from webbrowser import open_new_tab
import itertools as it
import BTCInput2 as btc
from app import wrapStringInHTMLMac3
import pydoc
import IPython
import cmd2
from cmd2 import style, fg, bg

#os.getcwd()

case_search_parser = argparse.ArgumentParser()
case_search_subparsers = case_search_parser.add_subparsers(title='subcommands', help='subcommand help')

save_html_parser = case_search_subparsers.add_parser('save_html',
                                                       help='year help')
save_html_parser.add_argument('-y', '--year', help='year the ruling was made')

view_case_parser = case_search_subparsers.add_parser('view_case',
                                                        help='view case help')
view_case_parser.add_argument('-y', '--year', help='year the ruling was made')

default_path = '/Users/thomassullivan/projects/GitHub/bulk_scotus/'

'''Note: not all of these commands will end up being included in the final
command line interface.

Note for 2/7/20: Add WrappedHTMLFormat properties to each class that we have created.'''

#import re

def error_msg(x):
    return cmd2.style(text=x, fg=cmd2.fg.yellow, bg=cmd2.bg.red,
                      bold=True)

def cleanhtml(raw_html):
  cleanr = re.compile('<.*?>')
  cleantext = re.sub(cleanr, '', raw_html)
  return cleantext


class ScotusCMD(cmd2.Cmd):
    '''
    The actual content of the commands should be moved to the app.py file.
    '''
    def __init__(self, use_ipython=True):
        super().__init__()
        self.self_in_py=True
        self.allow_style = 'Always'
        self.background_color = 'white'
        self.foreground_color = 'black'
        self.prompt='ScotusSearch'
        self.intro = cmd2.style(text='Welcome to ScotusSearch',
                                bg=self.background_color,
                                fg=self.foreground_color,
                                bold=True)
        self.default_path = '/Users/thomassullivan/projects/GitHub/bulk_scotus/'
        self.register_postloop_hook(self.reset_path)
        self.add_settable(cmd2.Settable('foreground_color', str,
                          'Foreground color to use with echo command',
                          choices=fg.colors()))
        self.add_settable(cmd2.Settable('background_color', str,
                          'Background color to use with echo command',
                          choices=bg.colors()))
        
    def reset_path(self) -> None:
        os.chdir(self.default_path)
        self.poutput(os.getcwd())
        return None
    
    def read_case(self, args):
        '''Displays the case in a pager on the screen'''
        os.chdir(self.default_path)
        cent_values = {17: '/1700s', 18:'/1800s', 19:'/1900s', 20: '/2000s'}
        try:
            assert len(args.year) == 4, 'the year is four digits long'
            assert args.year.isnumeric() == True, 'must enter a year'
        except AssertionError:
            self.poutput(error_msg('command entered incorrectly'))
            #print('command entered incorrectly')
        try:
            century = int(args.year[:2]) #make it into an integer to get the key
        except ValueError:
            self.poutput(error_msg('Incorrect year format'))
            #print('Incorrect year format')
        path = os.getcwd()
        path = path + cent_values.get(century)
        path2=path + '/'+args.year
        self.poutput(cmd2.style(f'files found in: {path2}',
                                bg=self.background_color,
                                fg=self.foreground_color))
       # print('the path of the individual year is: {0}'.format(path2))
        cases = [i for i in os.listdir(path2)]
        dir_file = path2+'/year_directory.json'
        with open(dir_file) as f:
            case_dict = json.load(f)
        category_list = [(k, style(f'{k} {v["id"]} {v["date"]} {v["judges"]}',
                          bg=cmd2.bg.white, fg=cmd2.fg.black)) \
                         for k, v in case_dict.items()]#  white_blue_bg(x=str(i))) for i in app.get_categories(session=self.session,
        choice = self.select(opts=category_list)
       #print('user choice is:', choice)
        #print(type(choice))
        try:
            choice = case_dict[choice]['id']
            print(choice)
        except KeyError:
            self.poutput(error_msg('Key not found, is this what you are looking for?'))
           # print('Key not found, is this what you are looking for?')
            choice = next( (key for key in case_dict if key.startswith(choice)), None )
            print(choice)
            continue_choice = btc.read_int_ranged(f'Continue with {choice}? 1-yes, 2-no', 1, 2)
            if continue_choice == 2:
                print('Search cancelled, return to main menu')
                return
            else:
                choice = case_dict[choice]['id']
        if choice == ".":
            self.poutput(error_msg('Search cancelled, returning to main menu'))
           # print('search cancelled, returning to main menu')
            return
        filename = choice + '.json'
        if filename in cases:
            os.chdir(path2)
            print(os.getcwd())
            with open(filename) as in_file:
                print(filename)
                new_case = json.load(in_file)
                new_case = new_case['html_with_citations']
                #new_case = cleanhtml(new_case)
                new_case = cmd2.style(new_case, bg=self.background_color,
                                      fg=self.foreground_color)
                IPython.core.page.page_dumb(new_case, start=0, screen_lines=25)
                os.chdir(default_path)

    def save_html(self, args):
        print(args.year)
        os.chdir(self.default_path)
        cent_values = {17: '/1700s', 18:'/1800s', 19:'/1900s', 20: '/2000s'}
        try:
            assert len(args.year) == 4, 'the year is four digits long'
            assert args.year.isnumeric() == True, 'must enter a year'
        except AssertionError:
            print('command entered incorrectly')
        try:
            century = int(args.year[:2]) #make it into an integer to get the key
        except ValueError:
            print('Incorrect year format')
        path = os.getcwd()
        path = path + cent_values.get(century)
        path2=path + '/'+args.year
        print('the path of the individual year is: {0}'.format(path2))
        cases = [i for i in os.listdir(path2)]
        dir_file = path2+'/year_directory.json'
        with open(dir_file) as f:
            case_dict = json.load(f)
        
        category_list = [(k, cmd2.style(text=f'{k} {v["id"]} {v["date"]} {v["judges"]}')) for k,
                         v in case_dict.items()]
        
        for k, v in case_dict.items():
            print(k, v['id'], v['date'], v['judges'])
        #print(category_list)
        choice = self.select(opts=category_list)
        print('user choice is:', choice)
        print(type(choice))
        try:
            choice = case_dict[choice]['id']
            print(choice)
        except KeyError:
            print('Key not found, is this what you are looking for?')
            #potentials = any(key.startswith(choice) for key in case_dict)
            choice = next( (key for key in case_dict if key.startswith(choice)), None )
            print(choice)
            continue_choice = btc.read_int_ranged(f'Continue with {choice}? 1-yes, 2-no', 1, 2)
            if continue_choice == 2:
                print('Search cancelled, return to main menu')
                return
            else:
                choice = case_dict[choice]['id']
        if choice == ".":
            print('search cancelled, returning to main menu')
            return
        filename = choice + '.json'
        if filename in cases:
            os.chdir(path2)
            print(os.getcwd())
            with open(filename) as in_file:
                print(filename)
                new_case = json.load(in_file)
                print('New case: ', new_case['html_with_citations'])
            #print('new case:' ,new_case.keys())
            filename_choice = btc.read_text('enter filename to save or "." to cancel: ')
            if filename_choice == '.':
                print('file creation cancelled')
                os.chdir(default_path)
                return
            else:
                wrapStringInHTMLMac3(program=filename_choice,
                                     body=new_case['html_with_citations'],
                                     url='test', default_path=default_path)
                os.chdir(default_path)

    save_html_parser.set_defaults(func=save_html)
    view_case_parser.set_defaults(func=read_case)

    @cmd2.with_argparser(case_search_parser)
    def do_case_search(self, args):
        """Search command help"""
        func = getattr(args, 'func', None)
        if func is not None:
            # Call whatever subcommand function was selected
            func(self, args)
        else:
            # No subcommand was provided, so call help
            self.do_help('search')
    
    def do_exit(self, arg):
        self.poutput(cmd2.style('Are you sure you want to quit? ',
                                bg=self.background_color,
                                fg=self.foreground_color, bold=False))
        exit_choice = self.select([(True, 'yes'), (False, 'no')])
        if exit_choice == True:
            self.poutput(cmd2.style('Existing ScotusCMD',
                                    bg=self.background_color,
                                    fg=self.foreground_color,
                                    bold=True))
            sys.exit()
        elif exit_choice == False:
            self.poutput('Returning to main menu')
        #print('Exiting ScotusCMD')
        #sys.exit()
        
if __name__ == '__main__':
    #import sys
    app = ScotusCMD()
    sys.exit(app.cmdloop())