# -*- coding: utf-8 -*-
import os
import time
import unittest
import logging
from configparser import ConfigParser
from pprint import pformat

from dpvs2004ContigFilter.dpvs2004ContigFilterImpl import dpvs2004ContigFilter
from dpvs2004ContigFilter.dpvs2004ContigFilterServer import MethodContext
from dpvs2004ContigFilter.authclient import KBaseAuth as _KBaseAuth

from installed_clients.AssemblyUtilClient import AssemblyUtil
from installed_clients.WorkspaceClient import Workspace



class dpvs2004ContigFilterTest(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        token = os.environ.get('KB_AUTH_TOKEN', None)
        config_file = os.environ.get('KB_DEPLOYMENT_CONFIG', None)
        cls.cfg = {}
        config = ConfigParser()
        config.read(config_file)
        for nameval in config.items('dpvs2004ContigFilter'):
            cls.cfg[nameval[0]] = nameval[1]
        # Getting username from Auth profile for token
        authServiceUrl = cls.cfg['auth-service-url']
        auth_client = _KBaseAuth(authServiceUrl)
        user_id = auth_client.get_user(token)
        # WARNING: don't call any logging methods on the context object,
        # it'll result in a NoneType error
        cls.ctx = MethodContext(None)
        cls.ctx.update({'token': token,
                        'user_id': user_id,
                        'provenance': [
                            {'service': 'dpvs2004ContigFilter',
                             'method': 'please_never_use_it_in_production',
                             'method_params': []
                             }],
                        'authenticated': 1})
        cls.wsURL = cls.cfg['workspace-url']
        cls.wsClient = Workspace(cls.wsURL)
        cls.serviceImpl = dpvs2004ContigFilter(cls.cfg)
        cls.scratch = cls.cfg['scratch']
        cls.callback_url = os.environ['SDK_CALLBACK_URL']
        suffix = int(time.time() * 1000)
        cls.wsName = "test_ContigFilter_" + str(suffix)
        ret = cls.wsClient.create_workspace({'workspace': cls.wsName})  # noqa
        cls.prepareTestData()

    @classmethod
    def prepareTestData(cls):
        """This function creates an assembly object for testing"""
        fasta_content = '>seq1 something soemthing asdf\n' \
                        'agcttttcat\n' \
                        '>seq2\n' \
                        'agctt\n' \
                        '>seq3\n' \
                        'agcttttcatgg'

        filename = os.path.join(cls.scratch, 'test1.fasta')
        with open(filename, 'w') as f:
            f.write(fasta_content)
        assemblyUtil = AssemblyUtil(cls.callback_url)
        cls.assembly_ref = assemblyUtil.save_assembly_from_fasta({
            'file': {'path': filename},
            'workspace_name': cls.wsName,
            'assembly_name': 'TestAssembly'
        })

    @classmethod
    def tearDownClass(cls):
        if hasattr(cls, 'wsName'):
            cls.wsClient.delete_workspace({'workspace': cls.wsName})
            print('Test workspace was deleted')

    # NOTE: According to Python unittest naming rules test method names should start from 'test'. # noqa
    # NOTE: According to Python unittest naming rules test method names should start from 'test'. # noqa
    def test_run_dpvs2004ContigFilter_ok(self):
        # call your implementation
        ret = self.serviceImpl.run_dpvs2004ContigFilter(self.ctx,
                                                {'workspace_name': self.wsName,
                                                 'assembly_input_ref': self.assembly_ref,
                                                 'min_length': 10
                                                 })

        # Validate the returned data
        self.assertEqual(ret[0]['n_initial_contigs'], 3)
        self.assertEqual(ret[0]['n_contigs_removed'], 1)
        self.assertEqual(ret[0]['n_contigs_remaining'], 2)

    def test_run_dpvs2004ContigFilter_min_len_negative(self):
        with self.assertRaisesRegex(ValueError, 'min_length parameter cannot be negative'):
            self.serviceImpl.run_dpvs2004ContigFilter(self.ctx,
                                              {'workspace_name': self.wsName,
                                               'assembly_input_ref': '1/fake/3',
                                               'min_length': '-10'})

    def test_run_dpvs2004ContigFilter_min_len_parse(self):
        with self.assertRaisesRegex(ValueError, 'Cannot parse integer from min_length parameter'):
            self.serviceImpl.run_dpvs2004ContigFilter(self.ctx,
                                              {'workspace_name': self.wsName,
                                               'assembly_input_ref': '1/fake/3',
                                               'min_length': 'ten'})
    
    def test_rundpvs2004ContigFilter_max(self):
        ref="79/16/1"
        result = self.serviceImpl.run_dpvs2004ContigFilter_max(self.ctx, {
            'workspace_name': self.wsName,
            'assembly_ref': ref,
            'min_length': 100,
            'max_length': 1000000
        })
        print(result)
        # TODO -- asssert some things (later)
        
    def test_run_dpvs2004ContigFilter_test_min(self):
        ref = "79/16/1"
        params = {
            'workspace_name': self.wsName,
            'assembly_ref': ref,
            'min_length': 200000,
            'max_length': 6000000
        }
        result = self.serviceImpl.run_dpvs2004ContigFilter_max(self.ctx, params)
        self.assertEqual(result[0]['n_total'], 2)
        self.assertEqual(result[0]['n_remaining'], 1)

    def test_run_dpvs2004ContigFilter_test_max(self):
        logging.info('Starting run_dpvs2004ContigFilter function. Params=' + pformat(params))

        # Step 1 - Parse/examine the parameters and catch any errors
        # It is important to check that parameters exist and are defined, and that nice error
        # messages are returned to users.  Parameter values go through basic validation when
        # defined in a Narrative App, but advanced users or other SDK developers can call
        # this function directly, so validation is still important.
        logging.info('Validating parameters.')
        if 'workspace_name' not in params:
            raise ValueError('Parameter workspace_name is not set in input arguments')
        workspace_name = params['workspace_name']
        if 'assembly_input_ref' not in params:
            raise ValueError('Parameter assembly_input_ref is not set in input arguments')
        assembly_input_ref = params['assembly_input_ref']
        if 'min_length' not in params:
            raise ValueError('Parameter min_length is not set in input arguments')
        min_length_orig = params['min_length']
        min_length = None
        try:
            min_length = int(min_length_orig)
        except ValueError:
            raise ValueError('Cannot parse integer from min_length parameter (' + str(min_length_orig) + ')')
        if min_length < 0:
            raise ValueError('min_length parameter cannot be negative (' + str(min_length) + ')')


        # Step 2 - Download the input data as a Fasta and
        # We can use the AssemblyUtils module to download a FASTA file from our Assembly data object.
        # The return object gives us the path to the file that was created.
        logging.info('Downloading Assembly data as a Fasta file.')
        assemblyUtil = AssemblyUtil(self.callback_url)
        fasta_file = assemblyUtil.get_assembly_as_fasta({'ref': assembly_input_ref})


        # Step 3 - Actually perform the filter operation, saving the good contigs to a new fasta file.
        # We can use BioPython to parse the Fasta file and build and save the output to a file.
        good_contigs = []
        n_total = 0
        n_remaining = 0
        for record in SeqIO.parse(fasta_file['path'], 'fasta'):
            n_total += 1
            if len(record.seq) >= min_length:
                good_contigs.append(record)
                n_remaining += 1

        logging.info('Filtered Assembly to ' + str(n_remaining) + ' contigs out of ' + str(n_total))
        filtered_fasta_file = os.path.join(self.shared_folder, 'filtered.fasta')
        SeqIO.write(good_contigs, filtered_fasta_file, 'fasta')

        output = {
            'n_total': n_total,
            'n_remaining': n_remaining,
            'filtered_assembly_ref': new_ref
        }

        # Keep a list of contigs greater than min_length
        good_contigs = []
        # total contigs regardless of length
        n_total = 0
        # total contigs over the min_length
        n_remaining = 0
        for record in parsed_assembly:
            n_total += 1
            if len(record.seq) >= min_length and len(record.seq) <= max_length:
                good_contigs.append(record)
                n_remaining += 1

                 # Create a file to hold the filtered data
        workspace_name = params['workspace_name']
        filtered_path = os.path.join(self.shared_folder, 'filtered.fasta')
        SeqIO.write(good_contigs, filtered_path, 'fasta')
        # Upload the filtered data to the workspace
        new_ref = assembly_util.save_assembly_from_fasta({
            'file': {'path': filtered_path},
            'workspace_name': workspace_name,
            'assembly_name': fasta_file['assembly_name']
        })

        parsed_assembly = SeqIO.parse(fasta_file['path'], 'fasta')
        min_length = params['min_length']
        max_length = params['max_length']


        # Step 4 - Save the new Assembly back to the system
        logging.info('Uploading filtered Assembly data.')
        new_assembly = assemblyUtil.save_assembly_from_fasta({'file': {'path': filtered_fasta_file},
                                                              'workspace_name': workspace_name,
                                                              'assembly_name': fasta_file['assembly_name']
                                                              })


        # Step 5 - Build a Report and return
        reportObj = {
            'objects_created': [{'ref': new_assembly, 'description': 'Filtered contigs'}],
            'text_message': 'Filtered Assembly to ' + str(n_remaining) + ' contigs out of ' + str(n_total)
        }
        report = KBaseReport(self.callback_url)
        report_info = report.create({'report': reportObj, 'workspace_name': params['workspace_name']})


        # STEP 6: contruct the output to send back
        output = {'report_name': report_info['name'],
                  'report_ref': report_info['ref'],
                  'assembly_output': new_assembly,
                  'n_initial_contigs': n_total,
                  'n_contigs_removed': n_total - n_remaining,
                  'n_contigs_remaining': n_remaining
                  }
        logging.info('returning:' + pformat(output))
                
        #END run_dpvs2004ContigFilter

    def run_dpvs2004ContigFilter_max(self, ctx, params):
        """
        New app which filters contigs in an assembly using both a minimum and a maximum contig length
        :param params: instance of mapping from String to unspecified object
        :returns: instance of type "ReportResults" -> structure: parameter
           "report_name" of String, parameter "report_ref" of String
        """
        # ctx is the context object
        # return variables are: output
        #BEGIN run_dpvs2004ContigFilter_max
        n_total = 0

        for name in ['min_length', 'max_length', 'assembly_ref', 'workspace_name']:
            if name not in params:
                raise ValueError('Parameter "' + name + '" is required but missing')
        if not isinstance(params['min_length'], int) or (params['min_length'] < 0):
            raise ValueError('Min length must be a non-negative integer')
        if not isinstance(params['max_length'], int) or (params['max_length'] < 0):
            raise ValueError('Max length must be a non-negative integer')
        if not isinstance(params['assembly_ref'], str) or not len(params['assembly_ref']):
            raise ValueError('Pass in a valid assembly reference string')
        if not isinstance(params['max_length'], int) < (params['min_length']):
            raise ValueError('Max length must be greater than min length')
        
        assembly_util = AssemblyUtil(self.callback_url)
        fasta_file = assembly_util.get_assembly_as_fasta({'ref': params['assembly_ref']})
        print(fasta_file)
        
        output = {
            'n_total': n_total,
            'n_remaining': n_remaining
        }

        text_message = "".join([
            'Filtered assembly to ',
            str(n_remaining),
            ' contigs out of ',
            str(n_total)
        ])
        # Data for creating the report, referencing the assembly we uploaded
        report_data = {
            'objects_created': [
                {'ref': new_ref, 'description': 'Filtered contigs'}
            ],
            'text_message': text_message
        }
        # Initialize the report
        kbase_report = KBaseReport(self.callback_url)
        report = kbase_report.create({
            'report': report_data,
            'workspace_name': workspace_name
        })
        # Return the report reference and name in our results
        output = {
            'report_ref': report['ref'],
            'report_name': report['name'],
            'n_total': n_total,
            'n_remaining': n_remaining,
            'filtered_assembly_ref': new_ref
        }

        if not isinstance(output, dict):
            raise ValueError('Method run_dpvs2004ContigFilter_max return value ' +
                                'output is not type dict as required.')
            # return the results
        return [output]

        ref = "79/16/1"
        params = {
            'workspace_name': self.wsName,
            'assembly_ref': ref,
            'min_length': 100000,
            'max_length': 4000000
        }
        result = self.serviceImpl.run_dpvs2004ContigFilter_max(self.ctx, params)
        self.assertEqual(result[0]['n_total'], 2)
        self.assertEqual(result[0]['n_remaining'], 1)

        self.assertTrue(len(result[0]['report_name']))
        self.assertTrue(len(result[0]['report_ref']))

        self.assertTrue(len(result[0]['filtered_assembly_ref']))
    #END run_{username}ContigFilter_max

        def test_invalid_params(self):
            impl = self.serviceImpl
            ctx = self.ctx
            ws = self.wsName
            # Missing assembly ref
            with self.assertRaises(ValueError):
                impl.run_dpvs2004ContigFilter_max(ctx, {'workspace_name': ws,
                    'min_length': 100, 'max_length': 1000000})
            # Missing min length
            with self.assertRaises(ValueError):
                impl.run_dpvs2004ContigFilter_max(ctx, {'workspace_name': ws, 'assembly_ref': 'x',
                    'max_length': 1000000})
            # Min length is negative
            with self.assertRaises(ValueError):
                impl.run_dpvs2004ContigFilter_max(ctx, {'workspace_name': ws, 'assembly_ref': 'x',
                    'min_length': -1, 'max_length': 1000000})
            # Min length is wrong type
            with self.assertRaises(ValueError):
                impl.run_dpvs2004ContigFilter_max(ctx, {'workspace_name': ws, 'assembly_ref': 'x',
                    'min_length': 'x', 'max_length': 1000000})
            # Assembly ref is wrong type
            with self.assertRaises(ValueError):
                impl.run_dpvs2004ContigFilter_max(ctx, {'workspace_name': ws, 'assembly_ref': 1,
                    'min_length': 1, 'max_length': 1000000})
            with self.assertRaises(ValueError):
                impl.run_dpvs2004ContigFilter_max(ctx, {'workspace_name': ws, 'assembly-ref': 'x',
                    'min_length': 1, 'max_length': 100001})

