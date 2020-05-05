#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Mon May  4 07:46:04 2020

@author: thomassullivan
"""

import os
import argparse
import pprint
import cmd2
import sys
import datetime
import json
from webbrowser import open_new_tab
import itertools as it
import BTCInput2 as btc
from app import wrapStringInHTMLMac3
#os.getcwd()

default_path = '/Users/thomassullivan/projects/GitHub/bulk_scotus/'

'''Note: not all of these commands will end up being included in the final
command line interface.

Note for 2/7/20: Add WrappedHTMLFormat properties to each class that we have created.'''

class ScotusCMD(cmd2.Cmd):
    '''
    The actual content of the commands should be moved to the app.py file.
    '''
    def __init__(self):
        super().__init__()
        self.prompt='ScotusSearch'
        self.intro = 'Welcome to ScotusSearch'
        self.default_path = '/Users/thomassullivan/projects/GitHub/bulk_scotus/'
        self.register_postloop_hook(self.reset_path)
        
    def reset_path(self) -> None:
        os.chdir(self.default_path)
        self.poutput(os.getcwd())
        return None
    
    #prompt='ScotusSearch'
    #intro='Welcome to ScotusSearch'
    
    #def do_hello(self, line):
    #    print('hello ', line)
    
    # def do_search_year(self, line):
    #     try:
    #         os.chdir(self.default_path)
    #         cent_values = {17: '/1700s', 18:'/1800s', 19:'/1900s', 20: '/2000s'}
    #         try:
    #             assert len(line) == 4, 'the year is four digits long'
    #             assert line.isnumeric() == True, 'must enter a year'
    #         except AssertionError:
    #             print('command entered incorrectly')
    #         try:
    #             century = int(line[:2]) #make it into an integer to get the key
    #         except ValueError:
    #             print('Incorrect year format')
    #         path = os.getcwd()
    #         path = path + cent_values.get(century)
    #         #print('the new path is', path)
    #         #print(os.listdir(path))
    #         path2=path + '/'+line
    #         print('the path of the individual year is: {0}'.format(path2))
    #         #print('these cases were decided that year:', os.listdir(path2))
    #         cases = [i for i in os.listdir(path2)]
    #         #cases = None
    #         dir_file = path2+'/year_directory.json'
    #         with open(dir_file) as f:
    #             case_dict = json.load(f)
    #         for k, v in case_dict.items():
    #             print(k, v['id'], v['date'], v['judges'])
    #         #print(case_dict)
    #         #with open('year_directory.json') as f:
    #         #    cases = json.load(f)
    #         #    pprint.pprint(cases)
    #         choice = btc.read_text('choose a case to view in html or "." to cancel: ')
    #         try:
    #             choice = case_dict[choice]['id']
    #         except KeyError:
    #             print('Key not found, is this what you are looking for?')
    #             #potentials = any(key.startswith(choice) for key in case_dict)
    #             choice = next( (key for key in case_dict if key.startswith(choice)), None )
    #             print(choice)
    #             continue_choice = btc.read_int_ranged(f'Continue with {choice}? 1-yes, 2-no', 1, 2)
    #             if continue_choice == 2:
    #                 print('Search cancelled, return to main menu')
    #                 return
    #             else:
    #                 choice = case_dict[choice]['id']
    #             #print(choice)
    #             #confirm_choice = btc.read_int_ranged('1 to accept, 2 to return to main menu', 1, 2)
    #             #if confirm_choice ==2:
    #             #    print('search cancelled, return to main menu')
    #             #    return
    #             #or i in potentials:
    #                 #print(i)
    #             #return
    #         if choice == ".":
    #             print('search cancelled, returning to main menu')
    #             return
    #         filename = choice + '.json'
    #         if filename in cases:
    #             os.chdir(path2)
    #             print(os.getcwd())
    #             with open(filename) as in_file:
    #                 print(filename)
    #                 new_case = json.load(in_file)
    #             #print('new case:' ,new_case.keys())
    #             filename_choice = btc.read_text('enter filename to save or "." to cancel: ')
    #             if filename_choice == '.':
    #                 print('file creation cancelled')
    #                 os.chdir(default_path)
    #                 return
    #             else:
    #                 wrapStringInHTMLMac3(program=filename_choice,
    #                                      body=new_case['html_with_citations'],
    #                                      url='test', default_path=default_path)
    #                 os.chdir(default_path)
            
    #     except UnboundLocalError:
    #         print('year entered incorrectly')
    
    case_search_parser = argparse.ArgumentParser()      
    case_search_parser.add_argument('-y', '--year',
                                    help='year the decision was handed down')
    
    @cmd2.with_argparser(case_search_parser)
    def do_case_search(self, args):
        try:
            #print(args)
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
            #print('the new path is', path)
            #print(os.listdir(path))
            path2=path + '/'+args.year
            print('the path of the individual year is: {0}'.format(path2))
            #print('these cases were decided that year:', os.listdir(path2))
            cases = [i for i in os.listdir(path2)]
            #cases = None
            dir_file = path2+'/year_directory.json'
            with open(dir_file) as f:
                case_dict = json.load(f)
            for k, v in case_dict.items():
                print(k, v['id'], v['date'], v['judges'])
            #print(case_dict)
            #with open('year_directory.json') as f:
            #    cases = json.load(f)
            #    pprint.pprint(cases)
            choice = btc.read_text('choose a case to view in html or "." to cancel: ')
            try:
                choice = case_dict[choice]['id']
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
                    print(choice)
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
            
        except UnboundLocalError:
            print('year entered incorrectly')
            
    @cmd2.with_argparser(case_search_parser)
    def do_case_search2(self, args):
        #try:
            #print(args)
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
        #print('the new path is', path)
        #print(os.listdir(path))
        path2=path + '/'+args.year
        print('the path of the individual year is: {0}'.format(path2))
        #print('these cases were decided that year:', os.listdir(path2))
        cases = [i for i in os.listdir(path2)]
        #cases = None
        dir_file = path2+'/year_directory.json'
        with open(dir_file) as f:
            case_dict = json.load(f)
        
        category_list = [(k, f'{k} {v["id"]} {v["date"]} {v["judges"]}') for k, v in case_dict.items()]#  white_blue_bg(x=str(i))) for i in app.get_categories(session=self.session,
                                                                                    #section_id=args.section_id)]
        
        for k, v in case_dict.items():
            print(k, v['id'], v['date'], v['judges'])
        #print(case_dict)
        #with open('year_directory.json') as f:
        #    cases = json.load(f)
        #    pprint.pprint(cases)
        print(category_list)
        choice = self.select(opts=category_list)
        print('user choice is:', choice)
        print(type(choice))
        #choice = btc.read_text('choose a case to view in html or "." to cancel: ')
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

    #def do_EOF(self, line):
     #   return True
    
    def do_exit(self, arg):
        #del arg
        #a.close()
        print('Exiting ScotusCMD')
        sys.exit()
        
if __name__ == '__main__':
    #import sys
    app = ScotusCMD()
    sys.exit(app.cmdloop())