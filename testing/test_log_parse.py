""" Test log parsing

"""
import UserInterface


def main():
    infile = r"\\uwhis.hosp.wisc.edu\ufs\UWHealth\RadOnc\ShareAll\RayScripts\dev_logs\TPL_382\TPL_382.txt"

    important = []
    message = ''
    keep_phrases = ["CRITICAL", "INFO"]

    with open(infile) as f:
         f = f.readlines()

    for line in f:
        for phrase in keep_phrases:
            if phrase in line:
                important.append(line)
                message += line + '\n'
                break

    UserInterface.MessageBox(text=message, title='Boom goes the dynamite')


if __name__ == '__main__':
    main()