#!/usr/bin/env python

__author__ = "Doug Wendel"
__copyright__ = "Copyright 2010, The QIIME project"
__credits__ = ["Doug Wendel"]
__license__ = "GPL"
__version__ = "1.2.0-dev"
__maintainer__ = "Doug Wendel"
__email__ = "wendel@colorado.edu"
__status__ = "Development"

from data_access_connections import data_access_factory
from enums import ServerConfig
from sample_export import export_fasta_from_sample
import os
import stat
import threading

def submit_metadata_for_study(study_id, web_app_user_id, live_rest_services, debug = False):
    """
    Submits data to EBI SRA via REST services.

    This function takes the input options from the user and generates a url
    and request header for submitting to the EBI SRA system. 
    """
    
    submission_file_path = '/tmp/ebi_sra_submission_metadata_%s.xml' % study_id
    study_file_path = '/tmp/ebi_sra_study_metadata_%s.xml' % study_id
    #sample_file_path = '/tmp/ebi_sra_sample_metadata_%s.xml' % study_id
    #prep_file_path = '/tmp/ebi_sra_prep_metadata_%s.xml' % study_id
    #sequence_file_path = '/tmp/ebi_sra_sequence_metadata_%s.xml' % study_id
    #fasta_base_path = '/tmp/'

    # Set up a list of invalid values
    invalid_values = set(['', ' ', None, 'None'])

    # Get a copy of data access
    data_access = data_access_factory(ServerConfig.data_access_type)
    
    ######################################################
    #### Submission XML
    ######################################################
    
    # Get the study information
    study_info = data_access.getStudyInfo(study_id, web_app_user_id)
    
    submission_file = open(submission_file_path, 'w')
    submission_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    submission_file.write('<SUBMISSION_SET xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"\n')
    submission_file.write('xsi:noNamespaceSchemaLocation="ftp://ftp.sra.ebi.ac.uk/meta/xsd/sra_1_3/SRA.submission.xsd">\n')
    submission_file.write('<SUBMISSION alias="qiime_submission_{0}" center_name="CCME">\n'.format(str(study_id)))
    submission_file.write('<ACTIONS>\n')
    submission_file.write('    <ACTION>\n')
    submission_file.write('        <ADD source="qiime_study_{0}" schema="study"/>\n'.format(str(study_id)))
    submission_file.write('    </ACTION>\n')
    submission_file.write('    <ACTION>\n')
    submission_file.write('        <ADD source="qiime_sample_{0}" schema="sample"/>\n'.format(str(study_id)))
    submission_file.write('    </ACTION>\n')
    submission_file.write('    <ACTION>\n')
    submission_file.write('        <ADD source="qiime_experiment_{0}" schema="experiment"/>\n'.format(str(study_id)))
    submission_file.write('    </ACTION>\n')
    submission_file.write('    <ACTION>\n')
    submission_file.write('        <ADD source="qiime_run_{0}" schema="run"/>\n'.format(str(study_id)))
    submission_file.write('    </ACTION>\n')
    submission_file.write('</ACTIONS>\n')
    submission_file.write('</SUBMISSION>\n')
    submission_file.write('</SUBMISSION_SET>\n')    

    ######################################################
    #### Study Submission
    ######################################################

    print 'STUDY'

    # Get the study info and put it into xml format for MG-RAST
    study_file = open(study_file_path, 'w')
    
    # Don't want to write these to EBI
    del study_info['mapping_file_complete']
    del study_info['can_delete']
    del study_info['project_id']
    del study_info['lab_person_contact']
    del study_info['emp_person']
    del study_info['has_extracted_data']
    del study_info['number_samples_promised']
    del study_info['spatial_series']
    del study_info['first_contact']
    del study_info['has_physical_specimen']
    del study_info['avg_emp_score']
    del study_info['user_emp_score']
    del study_info['lab_person']
    del study_info['principal_investigator']
    del study_info['principal_investigator_contact']
    del study_info['most_recent_contact']

    study_file.write('<?xml version="1.0" encoding="UTF-8"?>')
    study_file.write('<STUDY_SET xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')
    study_file.write('    xsi:noNamespaceSchemaLocation="ftp://ftp.sra.ebi.ac.uk/meta/xsd/sra_1_3/SRA.study.xsd">')
    study_file.write('    <STUDY alias="qiime_study_{0}"'.format(str(study_id)))
    study_file.write('        center_name="CCME">')
    study_file.write('        <DESCRIPTOR>')
    study_file.write('            <STUDY_TITLE>{0}</STUDY_TITLE>'.format(study_info['study_title']))
    study_file.write('            <STUDY_TYPE existing_study_type="{0}"/>'.format(study_info['study_type']))
    study_file.write('            <STUDY_ABSTRACT>{0}</STUDY_ABSTRACT>'.format(study_info['study_abstract']))
    study_file.write('        </DESCRIPTOR>')
    study_file.write('        <STUDY_ATTRIBUTES>')
    
    # Write out the remaining study fields
    for item in study_info:
        value = study_info[item]
        # Skip blank or null values
        if value in invalid_values:
            continue
        study_file.write('            <STUDY_ATTRIBUTE>')
        study_file.write('                <TAG>{0}</TAG>'.format(item))
        study_file.write('                <VALUE>{0}</VALUE>'.format(value))
        study_file.write('            </STUDY_ATTRIBUTE>')
        
    study_file.write('        </STUDY_ATTRIBUTES>')
    study_file.write('    </STUDY>')
    study_file.write('</STUDY_SET>')
    
    study_file.close()

    # Read the study file
    #study_file = open(study_file_path, 'r')
    #file_contents = study_file.read()
    
    # Output for debugging
    #if debug:
    #    print file_contents
    
    #study_file.close()

    # Send the data to MG-RAST via REST services
    #success, project_id = live_rest_services.send_post_data(study_cgi_path, file_contents, host, debug)
    #if not project_id:
    #    print 'Failed to add study metadata to MG-RAST. Aborting...'
    #    return

    ######################################################
    #### Sample Submission
    ######################################################

    # Get the column for this study and bin them into sample and prep lists
    study_columns = data_access.getStudyActualColumns(study_id)

    # Find the samples for this study
    samples = data_access.getSampleList(study_id)

    # For every sample, get the details and write them to the sample file
    for sample_id in samples:
        print 'SAMPLE'

        # Assign the sample name for later use
        sample_name = samples[sample_id]

        # Open the sample file for writing
        sample_file = open(sample_file_path, 'w')

        # Write the sample information to the sample file
        sample_file.write('<data_block>\n')
        sample_file.write('    <sample>\n')
        sample_file.write("        <study_id namespace='qiime'>%s</study_id>\n" % study_id)
        sample_file.write('        <project_id>%s</project_id>\n' % project_id)
        sample_file.write("        <sample_id namespace='qiime'>%s</sample_id>\n" % sample_id)
        sample_file.write('        <sample_name>%s</sample_name>\n' % sample_name)
        sample_file.write('        <metadata>\n')

        # A few values necessary to run findMetadataTable
        lock = threading.Lock()
        log = []
        field_type = 'text'

        # For each column for this sample, write the value to the sample file
        for column_name in study_columns:
            table_name = data_access.findMetadataTable(column_name, field_type, log, study_id, lock)
            if not table_name:
                continue
            table_category = data_access.getTableCategory(table_name)

            # Skip the prep and study columns
            if table_category in ['prep', 'study']:
                continue

            #print table_name, column_name, sample_id
            column_value = data_access.getSampleColumnValue(sample_id, table_name, column_name)
            # Skip blank or null values
            if column_name in invalid_values:
                print 'Skipping non-value for column %s in table %s for sample %s (value is: "%s")' % (column_name, table_name, sample_id, str(column_value))
                continue

            sample_file.write('            <{0}>{1}</{0}>\n'.format(column_name,
                                                                    clean_value_for_mgrast(column_value)))

        sample_file.write('        </metadata>\n')
        sample_file.write('    </sample>\n')
        sample_file.write('</data_block>\n')

        #Close the file and re-open for reading
        sample_file.close()
        sample_file = open(sample_file_path, 'r')
        file_contents = sample_file.read()
        sample_file.close()

        # Send the data to MG-RAST via REST services
        success, mgrast_sample_id = live_rest_services.send_post_data(sample_cgi_path, file_contents, host, debug)
        if not success or not mgrast_sample_id:
            print 'Failed to add sample metadata to MG-RAST for sample_id %s: %s. Skipping sample and its dependencies...'\
            % (sample_id, sample_name)
            continue

        ######################################################
        #### Sequence Prep Submission
        ######################################################

        for sample_id, row_number in data_access.getPrepList(sample_id):
            print 'PREP'
            # Open the prep file for writing
            prep_file = open(prep_file_path, 'w')

            prep_file.write('<data_block>\n')
            prep_file.write('    <sample_prep>\n')
            prep_file.write('        <study_id>%s</study_id>\n' % study_id)
            prep_file.write('        <project_id>%s</project_id>\n' % project_id)
            prep_file.write("        <sample_id namespace='qiime'>%s</sample_id>\n" % sample_id)
            prep_file.write("        <sample_id namespace='mgrast'>%s</sample_id>\n" % mgrast_sample_id)
            prep_file.write('        <sample_name>%s</sample_name>\n' % sample_name)
            prep_file.write('        <row_number>%s</row_number>\n' % row_number)
            prep_file.write('        <metadata>\n')

            # A few values necessary to run findMetadataTable
            lock = threading.Lock()
            log = []
            field_type = 'text'

            # For each column for this sample, write the value to the sample file
            for column_name in study_columns:
                table_name = data_access.findMetadataTable(column_name, field_type, log, study_id, lock)
                table_category = data_access.getTableCategory(table_name)

                # Skip the prep and study columns
                if table_category != 'prep':
                    continue

                column_value = data_access.getPrepColumnValue(sample_id, row_number, table_name, column_name)
                # Skip blank or null values
                if column_value in invalid_values:
                    continue

                prep_file.write('            <{0}>{1}</{0}>\n'.format(column_name,
                                                                      clean_value_for_mgrast(column_value)))

            prep_file.write('        </metadata>\n')
            prep_file.write('    </sample_prep>\n')
            prep_file.write('</data_block>\n')

            #Close the file and re-open for reading
            prep_file.close()
            prep_file = open(prep_file_path, 'r')
            file_contents = prep_file.read()
            prep_file.close()

            # Send the data to MG-RAST via REST services
            success, entity_id = live_rest_services.send_post_data(prep_cgi_path, file_contents, host, debug)
            if not success:
                print 'Failed to add prep metadata to MG-RAST for sample_id %s. Skipping sample and its dependencies...' % sample_id
                continue

            ######################################################
            #### Fasta Submission
            ######################################################

            print 'FASTA'

            # If there are no sequences then skip
            output_fasta_path = fasta_base_path + 'sequences_%s_%s.fasta' % (sample_id, row_number)
            export_fasta_from_sample(study_id, sample_id, output_fasta_path)
            file_size = os.stat(output_fasta_path)[stat.ST_SIZE]
            if file_size == 0:
                continue

            # Open the prep file for writing
            sequence_file = open(sequence_file_path, 'w')

            sequence_file.write('<data_file>\n')
            sequence_file.write('     <study_id>%s</study_id>\n' % study_id)
            sequence_file.write('     <project_id>%s</project_id>\n' % project_id)
            sequence_file.write("     <sample_id namespace='qiime'>%s</sample_id>\n" % sample_id)
            sequence_file.write("     <sample_id namespace='mgrast'>%s</sample_id>\n" % mgrast_sample_id)
            sequence_file.write('     <row_number>%s</row_number>\n' % row_number)
            sequence_file.write("     <sequences type='16s'>\n")

            # For each column for this sample, write the value to the sample file
            f = open(output_fasta_path, 'r')
            sequence_file.write(f.read())
            f.close()

            sequence_file.write('     </sequences>\n')
            sequence_file.write('</data_file>\n')

            #Close the file and re-open for reading
            sequence_file.close()
            sequence_file = open(sequence_file_path, 'r')
            file_contents = sequence_file.read()
            sequence_file.close()

            # Send the data to MG-RAST via REST services
            success, entity_id = live_rest_services.send_post_data(sequence_cgi_path, file_contents, host, debug)
            if not success:
                print 'Failed to add sequence data to MG-RAST for sample_id %s, row_number %s.'\
                % (sample_id, row_number)


