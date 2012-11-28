'''
Decompile python byte encoded modules code. 
Created on Jul 19, 2011

@author: sean
'''

from __future__ import print_function

from argparse import ArgumentParser, FileType

import sys
import ast

from meta.asttools import print_ast, python_source
from meta.asttools.serialize import serialize, deserialize
import json
from meta.bytecodetools.pyc_file import extract 
from meta.decompiler.instructions import make_module
from meta.decompiler.disassemble import print_code
import os
from meta import asttools
from meta.asttools.visitors.pysourcegen import dump_python_source
from meta.decompiler.recompile import dump_pyc

py3 = sys.version_info.major >= 3

def depyc(args):
    
    binary = args.input.read()
    modtime, code = extract(binary)
    
    print("Decompiling module %r compiled on %s" % (args.input.name, modtime,), file=sys.stderr)
    
    if args.output_type == 'pyc':
        if py3 and args.output is sys.stdout:
            args.output = sys.stdout.buffer
        args.output.write(binary)
        return
            
    if args.output_type == 'opcode':
        print_code(code)
        return 
    
    mod_ast = make_module(code)
    
    if args.output_type == 'ast':
        json.dump(serialize(mod_ast), args.output, indent=2)
        return
    
    if args.output_type == 'python':
        python_source(mod_ast, file=args.output)
        return
        
    
    raise  Exception("unknow output type %r" % args.output_type)

def src_tool(args):
    print("Analysing python module %r" % (args.input.name,), file=sys.stderr)
    
    source = args.input.read()
    mod_ast = ast.parse(source, args.input.name)
    code = compile(source, args.input.name, mode='exec', dont_inherit=True)
    
    if args.output_type == 'opcode':
        print_code(code)
        return 
    elif args.output_type == 'ast':
        json.dump(serialize(mod_ast), args.output, indent=2)
        return 
    elif args.output_type == 'python':
        print(source.decode(), file=args.output)
    elif args.output_type == 'pyc':
        
        if py3 and args.output is sys.stdout:
            args.output = sys.stdout.buffer

        try:
            timestamp = int(os.fstat(args.input.fileno()).st_mtime)
        except AttributeError:
            timestamp = int(os.stat(args.input.name).st_mtime)
        if py3 and args.output is sys.stdout:
            args.output = sys.stdout.buffer
        codeobject = compile(source, '<recompile>', 'exec')
        dump_pyc(codeobject, args.output, timestamp=timestamp)
    else:
        raise  Exception("unknow output type %r" % args.output_type)

    return
def ast_tool(args):
    print("Reconstructing AST %r" % (args.input.name,), file=sys.stderr)
    
    mod_ast = deserialize(json.load(args.input))
    
    code = compile(mod_ast, args.input.name, mode='exec', dont_inherit=True)
    
    if args.output_type == 'opcode':
        print_code(code)
        return 
    elif args.output_type == 'ast':
        json.dump(serialize(mod_ast), args.output, indent=2)
        return 
    elif args.output_type == 'python':
        python_source(mod_ast, file=args.output)
        return
    elif args.output_type == 'pyc':
        
        if py3 and args.output is sys.stdout:
            args.output = sys.stdout.buffer

        try:
            timestamp = int(os.fstat(args.input.fileno()).st_mtime)
        except AttributeError:
            timestamp = int(os.stat(args.input.name).st_mtime)
        if py3 and args.output is sys.stdout:
            args.output = sys.stdout.buffer
        dump_pyc(code, args.output, timestamp=timestamp)
    else:
        raise  Exception("unknow output type %r" % args.output_type)

    return
    
def setup_parser(parser):
    parser.add_argument('input', type=FileType('rb'))
    parser.add_argument('-t', '--input-type', default='from_filename', dest='input_type', choices=['from_filename', 'python', 'pyc', 'ast'])
    
    parser.add_argument('-o', '--output', default='-', type=FileType('wb'))
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--python', default='python', action='store_const', const='python',
                        dest='output_type')
    group.add_argument('--ast', action='store_const', const='ast',
                        dest='output_type')
    group.add_argument('--opcode', action='store_const', const='opcode',
                        dest='output_type')
    group.add_argument('--pyc', action='store_const', const='pyc',
                        dest='output_type')
    
def main():
    parser = ArgumentParser(description=__doc__)
    setup_parser(parser)
    args = parser.parse_args(sys.argv[1:])
    
    
    if args.input_type == 'from_filename':
        from os.path import splitext
        root, ext = splitext(args.input.name)
        if ext in ['.py']:
            input_type = 'python'
        elif ext in ['.pyc', '.pyo']:
            input_type = 'pyc'
        elif ext in ['.ast', '.txt', '.json']:
            input_type = 'ast'
        else:
            raise SystemExit("Could not derive file type from extension please use '--input-type' option")
    else:
        input_type = args.input_type
        
    if input_type == 'python':
        src_tool(args)
    elif input_type == 'pyc':
        if py3 and args.input is sys.stdin:
            args.input = sys.stdin.buffer
        depyc(args)
    else:  # AST
        ast_tool(args)
        
        
        
if __name__ == '__main__':
    main()

