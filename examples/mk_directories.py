'''
Script to create directory structures for running of SMRF and iSnobal
'''

import os

#################
#### Inputs #####
#################

# enter basin, wy, and if it is operational or not
basin = 'brb'
wy = 2009
# is this operational or development
isops = True
# name of project if development
proj = 'testproj'
# string description of project
desc = ''

# path to starting drive
path_dr = '/home/micahsandusky/Documents/Code/awsfTesting/run1'

#####################
#### Doin stuff #####
#####################
# make basin path
path_ba = os.path.join(path_dr,basin)

# check if ops or dev
if isops:
    path_od = os.path.join(path_ba,'ops')
    # check if specified water year
    if len(str(wy)) > 1:
        path_wy = os.path.join(path_od,str(wy))
    else:
        path_wy = path_od

else:
    path_od = os.path.join(path_ba,'devel')
    path_proj = os.path.join(path_od, proj)

    if len(str(wy)) > 1:
        path_wy = os.path.join(path_proj,str(wy))
    else:
        path_wy = path_proj

# rigid directory work
print('AWSM creating directories')

if os.path.exists(path_dr):
    if not os.path.exists(path_wy):  # if the working path specified in the config file does not exist
        y_n = 'a'                        # set a funny value to y_n
        while y_n not in ['y','n']:      # while it is not y or n (for yes or no)
            y_n = raw_input('Directory %s does not exist. Create base directory and all subdirectories? (y n): '%path_wy)
        if y_n == 'n':
            print('Please fix the base directory (path_wy) in your config file.')
        elif y_n =='y':
            os.makedirs(os.path.join(path_wy, 'data/smrfOutputs/'))
            os.makedirs(os.path.join(path_wy, 'data/input/'))
            os.makedirs(os.path.join(path_wy, 'data/ppt_4b/'))
            os.makedirs(os.path.join(path_wy, 'data/forecast/'))
            os.makedirs(os.path.join(path_wy, 'runs/'))

        # look for description or prompt for one
        if len(desc) > 1:
            pass
        else:
            desc = raw_input('\nNo description for project. Enter one now:\n')
        # find where to write file
        if isops:
            fp_desc = os.path.join(path_od, 'projectDescription.txt')
        else:
            fp_desc = os.path.join(path_proj, 'projectDescription.txt')

        if not os.path.isfile(fp_desc):
            f = open(fp_desc, 'w')
            f.write(desc)
            f.close()
        else:
            print('Description file aleardy exists')


else:
    print('Base directory did not exit, not safe to conitnue')

paths = os.path.join(path_wy,'data/data/smrfOutputs')
