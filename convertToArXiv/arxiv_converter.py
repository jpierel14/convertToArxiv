from __future__ import print_function
import sys
import os
import shutil
import traceback
from optparse import OptionParser
from collections import Counter, defaultdict
from copy import copy
from tempfile import mkstemp
from shutil import move
from os import fdopen, remove

from .tex_utils import *

def replace_figure(orig_plot_fn, out_folder, file_mapping):

    possible_filenames = [orig_plot_fn + i for i in ['', '.pdf', '.png', '.eps']]
    print('plot filename:', end=' ')
    try:
        plot_filename = list(filter(os.path.isfile, possible_filenames))[0]
        print(plot_filename, '->', end=' ')
    except IndexError:
        print(orig_plot_fn, '[FILE NOT FOUND]')
        return None, None
    dest_filename = out_folder + os.path.basename(plot_filename)
    dest_ext = '.' + dest_filename.rsplit('.', 1)[1]
    try:
        dest_filename = file_mapping[plot_filename]
    except KeyError:
        tmp_filename = dest_filename
        counter = 0
        while os.path.isfile(dest_filename):
            counter += 1
            tmp_filename = dest_filename.replace(dest_ext, '') + str(counter).rjust(3,
                                                                                    '0') + dest_ext
        dest_filename = tmp_filename
        file_mapping[plot_filename] = dest_filename
    print('/'.join(dest_filename.rsplit('/', 2)[-2:]), end=' ')
    shutil.copy(plot_filename, dest_filename)
    print('[OK]')
    return plot_filename, os.path.basename(dest_filename).replace(dest_ext, '')

def get_affil(filename):
    f = FileIter(filename)
    affils=dict([])
    authors=dict([])
    orcs=dict([])
    affilProb=False
    commands=dict([])
    for line in f.get_line():
        if r'\newcommand{' in line or r'\renewcommand{' in line:
            command1=line[line.find('{')+1:line.find('}')]
            command2=line[line.rfind('{')+1:line.rfind('}')]
            commands[command1]=command2
        if r'\author' in line:
            if '[' in line:
                if '-' not in line:#make sure it isn't an orcid
                    key=line[line.find('[')+1:line.find(']')]
                    authors[simple_cmd_match.findall(line)[0][1]]=key
                    affilProb=True
                else:
                    orcs[simple_cmd_match.findall(line)[0][1]]=line[line.find('[')+1:line.find(']')]
        elif r'\affil' in line:
            if '[' in line:
                key=line[line.find('[')+1:line.find(']')]
                tempAffil=simple_cmd_match.findall(line)[0][1]
                if tempAffil[0]=='\\':
                    affils[key]=commands[tempAffil]
                else:
                    affils[key]=tempAffil
                affilProb=True

    if affilProb:
        return({k:[affils[z] for z in authors[k].split(',')] for k in authors.keys()}),None
    else:
        return None,orcs
                
            

def add_content_of_file(input_filename, output_file, output_folder, file_mapping, var_mapping, complex_cmds,
                        remove_comments=True,aas=False,graphicspath='.'):

    if not os.path.isfile(input_filename):
        input_filename += '.tex'
    f = FileIter(input_filename)
    if aas:
        firstAuthor=True
        authorAffils,orcids=get_affil(input_filename)
        if authorAffils is not None:
            authorFixed=False
        else:
            authorFixed=True
    else:
        authorFixed=True
    if 'abstract' in input_filename.lower():
        first=True
        last=True
    else:
        first=False
        last=False

    for line in f.get_line():

        if r'\documentclass' in line and aas:
                temp='\\documentclass[twocolumn]{aastex63}'+'\n'
                output_file.write(temp)
                output_file.write('\\received{\\today}'+'\n')
                output_file.write('\\revised{\\today}'+'\n')
                output_file.write('\\submitjournal{AAS}'+'\n')
                output_file.write('\\shorttitle{My Short Title}'+'\n')
                output_file.write('\\shortauthors{Author et al.}'+'\n')
                continue
        if r'\author' in line and not authorFixed:
            temp=line.replace(line[line.find('['):line.find(']')+1],'')
            author=simple_cmd_match.findall(temp)[0][1]
            if firstAuthor:
                output_file.write('\\correspondingauthor{'+author+'}\n')
                output_file.write('\\email{myemail}\n')
                firstAuthor=False
            if orcids is not None and author in orcids.keys():
                temp='['+orcids[author]+']'+temp
            output_file.write(temp+'\n')
            
            for k in authorAffils[author]:

                output_file.write('\\affil{'+k+'}'+'\n')

            continue
        if r'\affil' in line and not authorFixed:
            continue

        if aas:

            if first and r'\begin{abstract}' not in line:
                output_file.write('\\begin{abstract}\n')
                first=False
            if r'\date' in line:
                continue
            if r'\abstract' in line:
                continue
            line=line.replace(r'\xspace','')
            line=line.replace(r'\begin{dmath}','\\begin{equation}')
            line=line.replace(r'\end{dmath}','\\end{equation}')

            if '{figure}[' in line:
                line=line[:line.find('[')+1]+'ht!]\n'
            elif '{figure*}[' in line:
                line=line[:line.find('[')+1]+'t]\n'
            if r'\maketitle' in line or 'Affilfont' in line or 'pagestyle' in line or 'multicols' in line:
                continue
            elif r'\bottomrule' in line:
                line=line.replace('bottomrule','hline')
            elif r'\midrule' in line:
                line=line.replace('midrule','hline')

        if r'\newcommand{' not in line and r'\renewcommand{' not in line:
            for var_name, var_val in sorted(var_mapping.items(), key=lambda x:
            len(x[0]), reverse=True):
                if var_name not in complex_cmds:
                    line = line.replace(var_name, var_val)
        if not line.strip().startswith('%'):
            if '%' in line and remove_comments:
                cleaned_line = list()
                for part in line.split('%'):
                    cleaned_line.append(part)
                    if not part.endswith('\\'):
                        break
                line = '%'.join(cleaned_line)
                line += '%'
                if not line.endswith('\n'):
                    line += '\n'

            line_simple_cmd = simple_cmd_match.findall(line.strip())
            # print(line.strip(), '\n\t->', line_simple_cmd)
            if r'\graphicspath{' in line:
                temp=simple_cmd_match.findall(line)
                graphicspath=temp[0][1].strip('{').strip('}').strip('/')


            elif r'\input{' in line: 
                for cmd, import_filename in simple_cmd_match.findall(line):
                    

                    if cmd == 'input':
                        if not remove_comments:
                            output_file.write('%' + '=' * 80 + '\n')
                            output_file.write('%imported external file: ' + import_filename + '\n')
                        print('import external file content:', import_filename)
                        add_content_of_file(import_filename, output_file, output_folder, file_mapping, var_mapping,
                                            complex_cmds, remove_comments=remove_comments,aas=aas)
                        if not remove_comments:
                            output_file.write('%end external file: ' + import_filename + '\n')
                            output_file.write('%' + '=' * 80 + '\n')
                        print('import external file content:', import_filename, '[DONE]')
            elif r'\includegraphics' in line:
                line = line[line.find(r'\includegraphics'):]
                if '[' in line[:line.find('{')]:
                    extra=line[line.find('['):line.find(']')+1]
                    
                    tempLine=line.replace(extra,'')
                else:
                    tempLine=copy(line)
                orig_plot_fn =simple_cmd_match.findall(tempLine)[0][1]
                    
                orig_fn, dest_fn = replace_figure(os.path.join(graphicspath,orig_plot_fn), output_folder, file_mapping)
                if orig_fn is not None:
                    line = line.replace(orig_plot_fn, dest_fn)

                if aas:
                    if 'center' in line:
                        if line[line.find('center')-1]=='[':
                            if line[line.find('center')+len('center')]==']':
                                line=line.replace('[center]','')
                            else:
                                line=line.replace('center,','')
                        else:
                            line=line.replace(',center','')
                output_file.write(line)
            elif r'\bibliography{' in line:
                compiled_bibtex_file = input_filename.replace('.tex', '.bbl')
                if not os.path.isfile(compiled_bibtex_file):
                    article_file = input_filename.replace('.tex', '')
                    if not os.path.isfile(input_filename.replace('.tex', '.aux')):
                        print('try compile paper:', end=' ')
                        sys.stdout.flush()
                        if os.system('pdflatex ' + article_file) == 0:
                            print('[OK]')

                        else:
                            print('[FAILED]')
                    print('try compile paper:', end=' ')
                    sys.stdout.flush()
                    if os.system('bibtex ' + article_file) == 0:
                        print('[OK]')
                    else:
                        print('[FAILED]')
                try:
                    if not remove_comments:
                        output_file.write('%' + '=' * 80 + '\n')
                        output_file.write('% bibtex content\n')
                    with open(compiled_bibtex_file, 'r') as bib_f:
                        for bib_line in bib_f:
                            if not bib_line.strip().startswith('%') or not remove_comments:
                                output_file.write(bib_line)
                    if not remove_comments:
                        output_file.write('\n% end bibtex\n')
                        output_file.write('%' + '=' * 80 + '\n')
                except:
                    print(traceback.format_exc())
            elif r'\newcommand{' in line or r'\renewcommand{' in line:

                if ('rule' in line.lower() or 'acknowledgments' in line.lower() or 'abstract' in line.lower() or 'appendix' in line.lower()) and aas:
                    continue
                #print('newcmd line:', line)
                # \newcommand{\varname}{var_val}
                braces_counter = defaultdict(int, Counter(line))
                braces = braces_counter['{'] - braces_counter['}']
                output_file.write(line)
                if braces == 0:
                    for var_name, var_val in newcmd_match.findall(line):
                        var_mapping[var_name] = var_val
                        # print('map var:',var_name, var_val)
                else:
                    tmp_cmd = [line.strip()]
                    cmd_name = line_simple_cmd[0][1]
                    for line in f.get_line():
                        if '%' in line:
                            if 'http:' in line:
                                line = line.replace('%',r'\%')
                            else:
                                line = line.split('%', 1)[0] + '%\n'
                                if line.strip() == '%':
                                    continue
                        if r'\newcommand{' not in line and r'\renewcommand{' not in line:
                            for var_name, var_val in var_mapping.items():
                                if var_name not in complex_cmds:
                                    line = line.replace(var_name, var_val)
                        output_file.write(line)
                        tmp_cmd += [line.strip()]
                        braces_counter = defaultdict(int, Counter(line))
                        braces += braces_counter['{'] - braces_counter['}']
                        #print('-'*80)
                        #print('line:', line)
                        #print('open braces:', braces)

                        if braces <= 0:
                            break
                    if any(map(lambda x: r'\includegraphics' in x, tmp_cmd)):
                        tmp_cmd = '\n'.join(tmp_cmd[1:-1])
                        #print('new cmd:', cmd_name)
                        #print(tmp_cmd)
                        complex_cmds[cmd_name] = tmp_cmd
            elif r'\usepackage' in line:
                if aas:
                    continue
                temp=simple_cmd_match.findall(line)
                pack=temp[0][1]
                pack=pack[pack.rfind('/')+1:]
                output_file.write("\\"+temp[0][0]+'{'+pack+'}'+'\n')
            

            elif len(line_simple_cmd) > 0:
                if 'fancy' in line and aas:
                    continue
                cmd = "\\" + line_simple_cmd[0][0]
                #print('\tcmd', cmd)
                #print(complex_cmds.keys())
                if cmd in complex_cmds:
                    vars = get_vars(line)
                    cmd = complex_cmds[cmd]
                    #print('ORIG CMD:', cmd)
                    #print('vars:', vars)
                    for idx, var in enumerate(vars):
                        cmd = cmd.replace('#' + str(idx + 1), var)
                    #print('WRITE cmd:', cmd)
                    #print('-'*80)
                    for cmd_line in cmd.split('\n'):
                        for orig_plot_fn in graphics_cmd_match.findall(cmd_line):
                            orig_fn, dest_fn = replace_figure(orig_plot_fn, output_folder, file_mapping)
                            if orig_fn is not None:
                                cmd_line = cmd_line.replace(orig_plot_fn, dest_fn)

                        output_file.write(cmd_line + '\n')
                        #print(cmd_line)
                    #print('-'*80)
                else:
                    output_file.write(line)
            else:
                output_file.write(line)
        elif not remove_comments:
            output_file.write(line)
    if aas and last and r'\end{abstract}' not in line:
        output_file.write('\\end{abstract}\n')


def replace(file_path, pattern, subst):
    #Create temp file
    fh, abs_path = mkstemp()
    with fdopen(fh,'w') as new_file:
        with open(file_path) as old_file:
            for line in old_file:
                new_file.write(line.replace(pattern, subst))
    #Remove original file
    remove(file_path)
    #Move new file
    move(abs_path, file_path)

