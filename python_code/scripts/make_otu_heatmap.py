#!/usr/bin/env python
# File created on 11 Jun 2010
from __future__ import division

__author__ = "Jesse Stombaugh"
__copyright__ = "Copyright 2010, The QIIME WebApp project"
__credits__ = ["Jesse Stombaugh"]
__license__ = "GPL"
__version__ = "dev"
__maintainer__ = "Jesse Stombaugh"
__email__ = "jesse.stombaugh@colorado.edu"
__status__ = "Development"
 
from qiime.util import parse_command_line_parameters, get_options_lookup
from optparse import make_option
from os import makedirs,path,system
from qiime.util import load_qiime_config
from generate_mapping_and_otu_table import write_mapping_and_otu_table
from submit_job_to_qiime import submitQiimeJob
from qiime.parse import parse_qiime_parameters
from qiime.workflow import print_to_stdout,\
                           call_commands_serially,no_status_updates
from handler_workflows import run_make_otu_heatmap_html
from cogent.app.util import get_tmp_filename

from data_access_connections import data_access_factory
from enums import ServerConfig
from submit_job_to_qiime import submitQiimeJob
from datetime import datetime
from time import strftime

qiime_config = load_qiime_config()
options_lookup = get_options_lookup()

script_info = {}
script_info['brief_description'] = "Run run_make_otu_heatmap_html function from handler_workflows.py in python_code of QIIME-DB"
script_info['script_description'] = """\
This script takes input from the DB, then associates the appropriate files and
parameters to the run_make_otu_heatmap_html function in the QIIME-DB """
script_info['script_usage'] = [("Example:","This is an example of a basic use case",
"%prog -f /files/on/server/ -w http://www.microbio.me/files/ -o /files/on/server/otu_table.biom -q /files/on/server/mapping_file.txt -p meta_analysis -u 0 -m 0 -b /files/on/server/params.txt -r 0 -s 1 -g /files/on/server/tree.tre -d 1/1/2012 -z /files/on/server/zip_files.zip -x http://www.microbio.me/zip_files.zip")]
script_info['output_description']= "There is no output from the script is puts the processed data into the Oracle DB."
script_info['required_options'] = [\
    make_option('-f','--fs_fp',help='this is the location of the actual files on the linux box'),\
    make_option('-w','--web_fp',help='this is the location that the webserver can find the files'),\
    make_option('-o','--otu_table_fp',help='this is the path to the otu table'),\
    make_option('-q','--mapping_file_fp',help='this is the path to the qiime mapping file'),\
    make_option('-p','--fname_prefix',help='this is the prefix to append to the users files'),\
    make_option('-u','--user_id',help='this is the user id'),\
    make_option('-m','--meta_id',help='this is the meta analysis id'),\
    make_option('-b','--params_path',help='this is the parameters file used'),\
    make_option('-r','--bdiv_rarefied_at',help='this is the rarefaction number'),\
    make_option('-s','--jobs_to_start',help='these are the jobs that should be started'),\
    make_option('-g','--tree_fp',help='this is the gg tree to use'),\
    make_option('-d','--run_date',help='this is the run date'),\
    make_option('-z','--zip_fpath',help='this is the zip fpath'),\
    make_option('-x','--zip_fpath_db',help='this is the zip_fpath_db'),\
]
script_info['optional_options'] = [\
]
script_info['version'] = __version__

def main():
    option_parser, opts, args =\
       parse_command_line_parameters(**script_info)

    #get all the options
    tmp_prefix=get_tmp_filename('',suffix='').strip()
    output_dir=path.join(opts.fs_fp,'heatmap','OTU_Heatmap_'+tmp_prefix)
    web_fp=path.join(opts.web_fp,'heatmap','OTU_Heatmap_'+tmp_prefix)
    otu_table_fp=opts.otu_table_fp
    mapping_file_fp=opts.mapping_file_fp
    file_name_prefix=opts.fname_prefix
    user_id=int(opts.user_id)
    meta_id=int(opts.meta_id)
    bdiv_rarefied_at=int(opts.bdiv_rarefied_at)
    jobs_to_start=opts.jobs_to_start
    tree_fp=opts.tree_fp
    command_handler=call_commands_serially
    zip_fpath=opts.zip_fpath
    zip_fpath_db=opts.zip_fpath_db
    run_date=opts.run_date
    force=True
    
    # get database connection
    try:
        from data_access_connections import data_access_factory
        from enums import ServerConfig
        import cx_Oracle
        data_access = data_access_factory(ServerConfig.data_access_type)
    except ImportError:
        print "NOT IMPORTING QIIMEDATAACCESS"
        pass
        
    # parse params
    try:
        parameter_f = open(opts.params_path)
    except IOError:
        raise IOError,\
         "Can't open parameters file (%s). Does it exist? Do you have read access?"\
         % opts.params_path
    
    params=parse_qiime_parameters(parameter_f)
    
    try:
        makedirs(output_dir)
    except OSError:
        if force:
            pass
        else:
            # Since the analysis can take quite a while, I put this check
            # in to help users avoid overwriting previous output.
            print "Output directory already exists. Please choose "+\
             "a different directory, or force overwrite with -f."
            exit(1)


    # run make otu heatmap
    heatmap_files=run_make_otu_heatmap_html(otu_table_fp, mapping_file_fp,
        output_dir, params, qiime_config,command_handler,tree_fp, 
        status_update_callback=no_status_updates)
    
    # zip the heatmap folder
    cd_dir=path.join(opts.fs_fp,'heatmap')
    cmd_call='cd %s; zip -r %s %s' % (cd_dir,zip_fpath,output_dir.split('/')[-1])
    system(cmd_call)
    
    #convert link into web-link
    web_link=path.join(web_fp,path.splitext(otu_table_fp.split('/')[-1])[0]+'.html')
    
    # add the distance matrices
    valid=data_access.addMetaAnalysisFiles(True,int(meta_id),web_link,'HEATMAP',run_date,'HEATMAP')
    if not valid:
        raise ValueError, 'There was an issue uploading the filepaths to the DB!'

    
    
if __name__ == "__main__":
    main()
