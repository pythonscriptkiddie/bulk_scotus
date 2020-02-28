DEBUG_MODE = True

from dateutil.parser import parse

#create read_date function

def read_text(prompt):
    '''
    Displays a prompt and reads in a string of text.
    Keyboard interrupts (CTRL+C) are ignored
    returns a string containing the string input by the user
    '''
    while True:  # repeat forever
        try:
            result=input(prompt) # read the input
            # if we get here no exception was raised
            if result=='':
                #don't accept empty lines
                print('Please enter text')
            else:
                # break out of the loop
                break
        except KeyboardInterrupt:
            # if we get here the user pressed CTRL+C
            print('Please enter text')
            if DEBUG_MODE:
                raise Exception('Keyboard interrupt')

    # return the result
    return result

#def read_bool(prompt='y or n', yes='y', no='n', yes_option='confirm', no_option='cancel'):
#    choice_string = ' '+ '{0} to {1}, {2} to {3} '.format( 
#                           yes, yes_option, no, no_option)
#    #The choice_string formats the choices that the user has to make when
#    #making a yes or no decision
#    while True:
#        choice = read_text(prompt=prompt+choice_string+' ')
#        if choice == yes:
#            return True
#        elif choice == no:
#            return False
#        else:
#            print('Please enter {0} to {1}, {1} to {2}')

def read_bool(decision='(y or n)', yes='y', no='n', yes_option='confirm', no_option='cancel'):
    choice_string = '{0} {1} to {2}, {3} to {4}: '.format(decision,
                          yes, yes_option, no, no_option)
    #The choice_string formats the choices that the user has to make when
    #making a yes or no decision
    while True:
        choice = read_text(prompt=choice_string)
        if choice == yes:
            return True
        elif choice == no:
            return False
        else:
            print('Invalid Entry')
#            print('Please enter {0} to {1}, {2} to {3}'.format(yes_option, yes, no_option, no))    

def read_date(prompt):
    '''
    Displays a prompt and reads in a date. Keyboard interrupts (CTRL+C) are
    ignored. Invalid dates are rejected. Returns a datetime.date object
    containing the value input by the user
    '''
    while True:
        try:
            date_text = read_text(prompt)
            #if date_text == '':
            #    print('please enter text')
            result = parse(date_text)
            result = result.date()
            break
    #pass
        except ValueError:
            print('Please enter a valid date')
            #pass
    return result

def read_number(prompt,function):
    '''
    Displays a prompt and reads in a floating point number.
    Keyboard interrupts (CTRL+C) are ignored
    Invalid numbers are rejected
    returns a float containing the value input by the user
    '''
    while True:  # repeat forever
        try:
            number_text=read_text(prompt)
            result=function(number_text) # read the input
            # if we get here no exception was raised
            # break out of the loop
            break
        except ValueError:
            # if we get here the user entered an invalid number
            print('Please enter a number')

    # return the result
    return result

def read_number_ranged(prompt, function, min_value, max_value):
    '''
    Displays a prompt and reads in a number.
    min_value gives the inclusive minimum value
    max_value gives the inclusive maximum value
    Raises an exception if max and min are the wrong way round
    Keyboard interrupts (CTRL+C) are ignored
    Invalid numbers are rejected
    returns a number containing the value input by the user
    '''
    if min_value>max_value:
        # If we get here the min and the max
        # are wrong way round
        raise Exception('Min value is greater than max value')
    while True:  # repeat forever
        result=read_number(prompt,function)
        if result<min_value:
            # Value entered is too low
            print('That number is too low')
            print('Minimum value is:',min_value)
            # Repeat the number reading loop
            continue 
        if result>max_value:
            # Value entered is too high
            print('That number is too high')
            print('Maximum value is:',max_value)
            # Repeat the number reading loop
            continue
        # If we get here the number is valid
        # break out of the loop
        break
    # return the result
    return result

def read_float(prompt):
    '''
    Displays a prompt and reads in a floating point number.
    Keyboard interrupts (CTRL+C) are ignored
    Invalid numbers are rejected
    returns a float containing the value input by the user
    '''
    return read_number(prompt,float)

def read_int(prompt):
    '''
    Displays a prompt and reads in an integer number.
    Keyboard interrupts (CTRL+C) are ignored
    Invalid numbers are rejected
    returns an int containing the value input by the user
    '''
    return read_number(prompt,int)

def read_float_ranged(prompt, min_value, max_value):
    '''
    Displays a prompt and reads in a floating point number.
    min_value gives the inclusive minimum value
    max_value gives the inclusive maximum value
    Raises an exception if max and min are the wrong way round
    Keyboard interrupts (CTRL+C) are ignored
    Invalid numbers are rejected
    returns a number containing the value input by the user
    '''
    return read_number_ranged(prompt,float,min_value,max_value)

def read_int_ranged(prompt, min_value, max_value):
    '''
    Displays a prompt and reads in an integer point number.
    min_value gives the inclusive minimum value
    max_value gives the inclusive maximum value
    Raises an exception if max and min are the wrong way round
    Keyboard interrupts (CTRL+C) are ignored
    Invalid numbers are rejected
    returns a number containing the value input by the user
    '''
    return read_number_ranged(prompt,int,min_value,max_value)


