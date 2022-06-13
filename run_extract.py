import sys
import re
import os
import json
import types
import math
import StringIO
import subprocess as subp
import argparse


mcpat_home = os.getenv("MCPAT_HOME", "/home/zhewen/repo/mcpat")
mcpat_bin = "mcpat"
gem5_home = os.getenv("GEM5_HOME", "/home/zhewen/repo/gem5-resources/src/parsec/gem5")

def construct_argparser():
    parser = argparse.ArgumentParser(description='writeStats')
    parser.add_argument('-n',
                        '--name',
                        nargs='+',
                        help='file to parse results',
                        default=[ \
                            'base_canneal_simsmall_64_0_4_4', \
                            'base_canneal_simsmall_64_0_4_8', \
                            'base_canneal_simsmall_64_0_8_4', \
                            'base_canneal_simsmall_64_0_8_8', \
                                ]
                        )
    return parser

class parse_node:
    def __init__(this,key=None,value=None,indent=0):
        this.key = key
        this.value = value
        this.indent = indent
        this.leaves = []
    
    def append(this,n):
        #print 'adding parse_node: ' + str(n) + ' to ' + this.__str__() 
        this.leaves.append(n)

    def get_tree(this,indent):
        padding = ' '*indent*2
        me = padding + this.__str__()
        kids = map(lambda x: x.get_tree(indent+1), this.leaves)
        return me + '\n' + ''.join(kids)
        
    def getValue(this,key_list):
        #print 'key_list: ' + str(key_list)
        if (this.key == key_list[0]):
            #print 'success'
            if len(key_list) == 1:
                return this.value
            else:
                kids = map(lambda x: x.getValue(key_list[1:]), this.leaves)
                #print 'kids: ' + str(kids) 
                return ''.join(kids)
        return ''        
        
    def __str__(this):
        return 'k: ' + str(this.key) + ' v: ' + str(this.value)

class parser:

    def dprint(this,astr):
        if this.debug:
            print(this.name)
            print(astr)

    def __init__(this, data_in):
        this.debug = False
        this.name = 'mcpat:mcpat_parse'

        buf = StringIO.StringIO(data_in)
      
        this.root = parse_node('root',None,-1)
        trunk = [this.root]

        for line in buf:
            
            #this.dprint('l: ' + str(line.strip()))

            indent = len(line) - len(line.lstrip())
            equal = '=' in line
            colon = ':' in line or 'L2' in line or 'L3' in line or 'NOC' in line
            useless = not equal and not colon
            items = map(lambda x: x.strip(), line.split('='))

            branch = trunk[-1]

            if useless: 
                # print('useless, '+ line)
                pass 

            elif equal:
                assert(len(items) > 1)

                n = parse_node(key=items[0],value=items[1],indent=indent)
                branch.append(n)

                # print('new parse_node: ' + str(n) )

            else:
                
                while ( indent <= branch.indent):
                    this.dprint('poping branch: i: '+str(indent) +\
                                    ' r: '+ str(branch.indent))
                    trunk.pop()
                    branch = trunk[-1]
                
                this.dprint('adding new leaf to ' + str(branch))
                n = parse_node(key=items[0],value=None,indent=indent)
                branch.append(n)
                trunk.append(n)
                
        
    def get_tree(this):
        return this.root.get_tree(0)

    def getValue(this,key_list):
        value = this.root.getValue(['root']+key_list) 
        if (value == ''):  
            print(key_list)
            assert False
        if 'Area' in key_list:
            if 'mm^2' in value: value = float(value.split(' ')[0])
        else:
            assert False
        return value

#runs McPAT and gives you the total energy in mJs
def main():
    argparser = construct_argparser()
    args = argparser.parse_args()

    plot_arr = []
    x_arr = list()
    
    for input_name in args.name:

        xmlfile = 'out/'+input_name+'.xml'
        command = mcpat_home
        command += "/" + mcpat_bin
        command += " -print_level 5"
        command += " -infile " + xmlfile
        #print command
        output = subp.check_output(command, shell=True)
        # print(output);exit()
        p = parser(output)

        ofname = 'out/'  + input_name + '.txt'
        f = open(ofname, "w")
        f.write(output)
        f.close()
        #print p.get_tree()

        metric = 'Area'
        core = p.getValue(['Processor:', 'Total Cores: 64 cores', metric])
        l3 = p.getValue(['Processor:', 'Total L3s:', metric])
        noc = p.getValue(['Processor:', 'Total NoCs (Network/Bus):', metric])
        l1i = p.getValue(['Core:', 'Instruction Fetch Unit:', 'Instruction Cache:',metric])*64
        l1d = p.getValue(['Core:', 'Load Store Unit:', 'Data Cache:',metric])*64
        l2 = p.getValue(['Core:', 'L2', metric])*64
        core_control = core - (l1i + l1d + l2)
        noc_buffer = p.getValue(['NOC', 'Router:','Virtual Channel Buffer:',  metric])*64
        noc_control = noc - noc_buffer

        plot_arr.append([core_control, l1i, l1d, l2, l3, noc_control, noc_buffer])
        
        num_vc = input_name.split('_')[-2]
        num_buf = input_name.split('_')[-1]
        cfg_name = 'vc'+num_vc+'buf'+num_buf
        x_arr.append(cfg_name)

    append = '_' + args.name[0].split('_')[-2] + '_' + args.name[0].split('_')[-1]
    base_name = args.name[0].replace(append, '')

    fn = 'out/'  + base_name + '_arr.txt'
    f = open(fn, "w")
    f.write(','.join(x_arr)+'\n')
    for i in plot_arr: f.write(''.join(str(i))+'\n')
    f.close()

    command = 'python3 plot.py -f out/' + base_name + '_arr.txt'
    output = subp.check_output(command, shell=True)
    print(output)
    

def getTimefromStats(name):
    firstdir = name.split('_')[0]
    realname = name.replace(firstdir+'_', '')
    statsFile = gem5_home + '/my_STATS/'+firstdir+'/'+realname+'/stats.txt'
    print("Reading simulation time from: " + statsFile)
    F = open(statsFile)
    ignores = re.compile(r'^---|^$')
    statLine = re.compile(r'([a-zA-Z0-9_\.:-]+)\s+([-+]?[0-9]+\.[0-9]+|[0-9]+|nan)')
    retVal = None
    for line in F:
        #ignore empty lines and lines starting with "---"  
        if not ignores.match(line):
            if "%" in line: continue
            statKind = statLine.match(line).group(1)
            statValue = statLine.match(line).group(2)
            if statKind == 'simSeconds':
                retVal = float(statValue)
    F.close()
    return retVal



if __name__ == '__main__':
    main()

