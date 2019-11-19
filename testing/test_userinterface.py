""" Test the UserInterface Module
Opens a simple dialog to test the user-interface library"""

import UserInterface
import sys


def test_simple_interface(check_list=True):
    if check_list:
        inputs = ['1', '2', '3', '4']
        color_inputs = ['Red', 'Blue', 'Green', 'Yellow']
        quest_inputs = ['To buy an argument.', 'To find the Holy Grail.', 'To beat Confucious in a foot race.']
        name_inputs = ['Arthur', 'Tarquin Fin-tim-lin-bin-whin-bim-lim-bus-stop-Ftang-Ftang-Ole-Biscuitbarrel']
        sample_dialog = UserInterface.InputDialog(
            title='Sample Interface',
            inputs={
                inputs[0]: 'What is your favorite color?',
                inputs[1]: 'What is your quest?',
                inputs[2]: 'What is your Name?',
                inputs[3]: 'What Is the Airspeed Velocity of an Unladen Swallow?'},
            datatype={
                inputs[0]: 'check',
                inputs[1]: 'combo',
                inputs[2]: 'combo'},
            initial={color_inputs[0]: '40'},
            options={
                inputs[0]: color_inputs,
                inputs[1]: quest_inputs,
                inputs[2]: name_inputs},
            required=[inputs[0], inputs[1]])
        options_response = sample_dialog.show()

        if options_response == {}:
            sys.exit('Selection of planning structure options was cancelled')

        message = ''
        for k, v in sample_dialog.values.iteritems():
            message += k + ' : ' + str(v) + '\n'

        UserInterface.MessageBox(message)


def main():
    test_simple_interface(check_list=True)


if __name__ == '__main__':
    main()
