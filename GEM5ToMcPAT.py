#!/usr/bin/python
from optparse import OptionParser
import sys
import re
import json
import types
import math
from xml.etree import ElementTree as ET
import os

gem5_home = os.getenv("GEM5_HOME", "/home/zhewen/repo/gem5-resources/src/parsec/gem5")

#This is a wrapper over xml parser so that 
#comments are preserved.
#source: http://effbot.org/zone/element-pi.htm
class PIParser(ET.XMLTreeBuilder):
   def __init__(self):
       ET.XMLTreeBuilder.__init__(self)
       # assumes ElementTree 1.2.X
       self._parser.CommentHandler = self.handle_comment
       self._parser.ProcessingInstructionHandler = self.handle_pi
       self._target.start("document", {})

   def close(self):
       self._target.end("document")
       return ET.XMLTreeBuilder.close(self)

   def handle_comment(self, data):
       self._target.start(ET.Comment, {})
       self._target.data(data)
       self._target.end(ET.Comment)

   def handle_pi(self, target, data):
       self._target.start(ET.PI, {})
       self._target.data(target + " " + data)
       self._target.end(ET.PI)

def parse(source):
    return ET.parse(source, PIParser())

def getname(rePath):
    return rePath.replace('my_STATS/','').replace('/',"_")

def main():
    global opts
    usage = "usage: %prog [options] <gem5 rePath> <template name>"
    parser = OptionParser(usage=usage)
    parser.add_option("-q", "--quiet", 
        action="store_false", dest="verbose", default=True,
        help="don't print status messages to stdout")
    (opts, args) = parser.parse_args()
    if len(args) != 2:
        parser.print_help()
        sys.exit(1)

    name = getname(args[0]) # arg 0 is the relative path of result dir from gem5 home
    stats_fname = gem5_home + '/' + args[0] + '/stats.txt'
    config_fname = gem5_home + '/' + args[0] + '/config.json'
    readStatsFile(stats_fname)
    readConfigFile(config_fname)
    readMcpatFile(args[1]) # arg 1 is the template name
    if not os.path.exists('out/'):
        os.makedirs('out/')
    dumpMcpatOut('out/'+name + '.xml')

def dumpMcpatOut(outFile):
    rootElem = templateMcpat.getroot()
    configMatch = re.compile(r'config\.([a-zA-Z0-9_:\.]+)')
    #replace params with values from the GEM5 config file 
    for param in rootElem.iter('param'):
        name = param.attrib['name']
        value = param.attrib['value']
        # print(name,value)
        # print(value)
        if 'config' in value:
            allConfs = configMatch.findall(value)
            for conf in allConfs:
                confValue = getConfValue(conf)
                # print(conf,confValue)
                value = re.sub("config."+ conf, str(confValue), value)
                # print(value)
            if "[" in value or ',' in value:
                exprs = re.split(',', value)
                exprs = [e.replace('[','').replace(']','') for e in exprs]
                # print(exprs)
                for i in range(len(exprs)):
                    exprs[i] = str(eval(exprs[i]))
                param.attrib['value'] = ','.join(exprs)
            else:
                param.attrib['value'] = str(eval(str(value)))

    #replace stats with values from the GEM5 stats file 
    statRe = re.compile(r'stats\.([a-zA-Z0-9_:\.]+)')
    for stat in rootElem.iter('stat'):
        name = stat.attrib['name']
        value = stat.attrib['value']
        if 'stats' in value:
            allStats = statRe.findall(value)
            expr = value
            for i in range(len(allStats)):
                if allStats[i] in stats:
                    expr = re.sub('stats.%s' % allStats[i], stats[allStats[i]], expr)
                else:
                    print "***WARNING: %s does not exist in stats***" % allStats[i]
                    print "\t Please use the right stats in your McPAT template file"

            if 'config' not in expr and 'stats' not in expr:
                stat.attrib['value'] = str(eval(expr))
    #Write out the xml file
    if opts.verbose: print "Writing input to McPAT in: %s" % outFile 
    templateMcpat.write(outFile)

def getConfValue(confStr):
    spltConf = re.split('\.', confStr) 
    currConf = config
    currHierarchy = ""
    for x in spltConf:
        currHierarchy += x
        if x not in currConf:
            if isinstance(currConf, types.ListType):
                #this is mostly for system.cpu* as system.cpu is an array
                #This could be made better
                if x not in currConf[0]:
                    print "%s does not exist in config" % currHierarchy 
                else:
                    currConf = currConf[0][x]
            else:
                    print "***WARNING: %s does not exist in config.***" % currHierarchy 
                    print "\t Please use the right config param in your McPAT template file"
        else:
            currConf = currConf[x]
        currHierarchy += "."
    return currConf
    

def readStatsFile(statsFile):
    global stats
    stats = {}
    if opts.verbose: print "Reading GEM5 stats from: %s" %  statsFile
    F = open(statsFile)
    ignores = re.compile(r'^---|^$')
    statLine = re.compile(r'([a-zA-Z0-9_\.:-]+)\s+([-+]?[0-9]+\.[0-9]+|[-+]?[0-9]+|nan|inf)')
    count = 0 
    for line in F:
        # print(line)
        #ignore empty lines and lines starting with "---"  
        if '%' in line: continue
        if not ignores.match(line):
            count += 1
            statKind = statLine.match(line).group(1)
            statValue = statLine.match(line).group(2)
            if statValue == 'nan':
                print "\tWarning (stats): %s is nan. Setting it to 0" % statKind
                statValue = '0'
            stats[statKind] = statValue
            # print(statKind, statValue)
    F.close()

def readConfigFile(configFile):
    global config
    if opts.verbose: print "Reading config from: %s" % configFile
    F = open(configFile)
    config = json.load(F)
    #print config
    #print config["system"]["membus"]
    #print config["system"]["cpu"][0]["clock"]
    F.close()

def readMcpatFile(templateFile):
    global templateMcpat 
    if opts.verbose: print "Reading McPAT template from: %s" % templateFile 
    templateMcpat = parse(templateFile)
    #print dir(templateMcpat)
    
    

if __name__ == '__main__':
    main()
