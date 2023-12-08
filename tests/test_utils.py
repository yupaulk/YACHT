import subprocess
from os.path import exists
import os
import numpy as np
import pandas as pd
# add the parent directory to the path
import sys
cpath = os.path.dirname(os.path.realpath(__file__))
project_path = os.path.join(cpath,'..')
sys.path.append(project_path)
from yacht import utils
import sourmash
import unittest
import math
import json
import pytest
import tempfile
import gzip
import sys
import shutil


def to_testing_data(file):
    return os.path.join(project_path, 'tests', os.path.join("testdata", file))


def test_load_signature_with_ksize1():
    # first, just try a *.sig file
    file = to_testing_data("sample.sig.zip")
    sig = utils.load_signature_with_ksize(file, 31)
    # right type?
    assert type(sig) == sourmash.signature.FrozenSourmashSignature
    # can we do a simple operation on it?
    assert sig.jaccard(sig) == 1.0


def test_load_signature_with_ksize2():
    # wrong k-size
    file = to_testing_data("sample.sig.zip")
    try:
        sig = utils.load_signature_with_ksize(file, 31)
    except ValueError:
        pass
    # wrong file type
    file = to_testing_data("foobar")
    try:
        sig = utils.load_signature_with_ksize(file, 31)
    except ValueError:
        pass
    # too many files
    try:
        sig = utils.load_signature_with_ksize(to_testing_data("20_genomes_sketches.zip"), 31)
    except ValueError:
        pass


def test_load_signature_with_ksize3():
    # different kind of format
    file = to_testing_data("sample.sig.zip")
    sig = utils.load_signature_with_ksize(file, 31)
    sourmash.save_signatures([sig], open(to_testing_data('test.sig.zip'), 'wb'), compression=1)
    sig = utils.load_signature_with_ksize(to_testing_data('test.sig.zip'), 31)
    assert type(sig) == sourmash.signature.FrozenSourmashSignature
    assert sig.jaccard(sig) == 1.0

class TestGetColumnIndices(unittest.TestCase):
    def test_1(self):
        column_name_to_index = {
            "TAXID": 1,
            "RANK": 0,
            "PERCENTAGE": 2,
            "TAXPATH": 3,
            "TAXPATHSN": 4
        }
        indices = utils.get_column_indices(column_name_to_index)
        assert indices == (0, 1, 2, 3, 4)

    def test_2(self):
        column_name_to_index = {
            "RANK": 0,
            "PERCENTAGE": 2,
            "TAXPATH": 3,
            "TAXPATHSN": 4
        }
        with self.assertRaises(RuntimeError):
            utils.get_column_indices(column_name_to_index)

    def test_3(self):
        column_name_to_index = {
            "TAXID": 1,
            "PERCENTAGE": 2,
            "TAXPATH": 3,
            "TAXPATHSN": 4
        }
        with self.assertRaises(RuntimeError):
            utils.get_column_indices(column_name_to_index)

    def test_4(self):
        column_name_to_index = {
            "TAXID": 1,
            "RANK": 0,
            "TAXPATH": 3,
            "TAXPATHSN": 4
        }
        with self.assertRaises(RuntimeError):
            utils.get_column_indices(column_name_to_index)

    def test_5(self):
        column_name_to_index = {
            "TAXID": 1,
            "RANK": 0,
            "PERCENTAGE": 2,
            "TAXPATHSN": 4
        }
        with self.assertRaises(RuntimeError):
            utils.get_column_indices(column_name_to_index)

    def test_6(self):
        column_name_to_index = {
            "TAXID": 1,
            "RANK": 0,
            "PERCENTAGE": 2,
            "TAXPATH": 3
        }
        indices = utils.get_column_indices(column_name_to_index)
        assert indices[4] is None

class TestGetCamiProfile(unittest.TestCase):
    def test_1(self):
        file_path = os.path.join(os.path.dirname(__file__), 'testdata/sample_cami.txt')
        with open(file_path, 'r') as file:
            sample_cami_content = file.readlines()

        profiles = utils.get_cami_profile(sample_cami_content)

        expected_header = {
            'SAMPLEID': 'CAMI_LOW_S001',
            'VERSION': '0.9.1',
            'RANKS': 'superkingdom|phylum|class|order|family|genus|species|strain',
            'TAXONOMYID': 'ncbi-taxonomy_DATE',
            '__PROGRAM__': 'unknown'
        }

        assert len(profiles) == 1
        sample_id, header, profile = profiles[0]

        assert sample_id == "CAMI_LOW_S001"
        assert header == expected_header
        assert len(profile) == 2044

        prediction1 = profile[0]
        assert prediction1.rank == 'superkingdom'
        assert prediction1.taxid == '2157'
        assert math.isclose(prediction1.percentage, 0.029528, abs_tol=1e-6)
        assert prediction1.taxpath == '2157'
        assert prediction1.taxpathsn == 'Archaea'

        prediction2 = profile[1]
        assert prediction2.rank == 'superkingdom'
        assert prediction2.taxid == '2'
        assert math.isclose(prediction2.percentage, 29.183763, rel_tol=1e-6)
        assert prediction2.taxpath == '2'
        assert prediction2.taxpathsn == 'Bacteria'


class TestStandardizeOutput(unittest.TestCase):
    def test_everything_exists(self):
        script_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        script_dir = os.path.join(script_dir, 'srcs')
        script_full_path = os.path.join(script_dir, 'standardize_yacht_output.py')
        assert os.path.exists(script_full_path)

        yacht_output = os.path.join(os.path.dirname(__file__), 'testdata/standardize_output_testdata/result.xlsx')
        assert os.path.exists(yacht_output)

        genome_to_taxid = os.path.join(os.path.dirname(__file__), 'testdata/standardize_output_testdata/toy_genome_to_taxid.tsv')
        assert os.path.exists(genome_to_taxid)

        outdir = os.path.join(os.path.dirname(__file__), 'testdata')
        assert os.path.exists(outdir)

        cmd = f"python {script_full_path} --yacht_output {yacht_output} --sheet_name min_coverage0.2 --genome_to_taxid {genome_to_taxid} --outfile_prefix cami_result --outdir {outdir}"
        res = subprocess.run(cmd, shell=True, check=True)
        assert res.returncode == 0
        assert os.path.exists(os.path.join(outdir, 'cami_result.cami'))

    def test_wrong_yacht_output(self):
        script_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        script_dir = os.path.join(script_dir, 'srcs')
        script_full_path = os.path.join(script_dir, 'standardize_yacht_output.py')
        assert os.path.exists(script_full_path)

        yacht_output = os.path.join(os.path.dirname(__file__), 'testdata/standardize_output_testdata/result_nonexisting.xlsx')
        assert not os.path.exists(yacht_output)

        genome_to_taxid = os.path.join(os.path.dirname(__file__), 'testdata/standardize_output_testdata/toy_genome_to_taxid.tsv')
        assert os.path.exists(genome_to_taxid)

        outdir = os.path.join(os.path.dirname(__file__), 'testdata')
        assert os.path.exists(outdir)

        cmd = f"python {script_full_path} --yacht_output {yacht_output} --sheet_name min_coverage0.2 --genome_to_taxid {genome_to_taxid} --outfile_prefix cami_result --outdir {outdir}"
        with self.assertRaises(subprocess.CalledProcessError):
            res = subprocess.run(cmd, shell=True, check=True)

    def test_wrong_genome_to_taxid(self):
        script_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        script_dir = os.path.join(script_dir, 'srcs')
        script_full_path = os.path.join(script_dir, 'standardize_yacht_output.py')
        assert os.path.exists(script_full_path)

        yacht_output = os.path.join(os.path.dirname(__file__), 'testdata/standardize_output_testdata/result.xlsx')
        assert os.path.exists(yacht_output)

        genome_to_taxid = os.path.join(os.path.dirname(__file__), 'testdata/standardize_output_testdata/toy_genome_to_taxid_nonexisting.tsv')
        assert not os.path.exists(genome_to_taxid)

        outdir = os.path.join(os.path.dirname(__file__), 'testdata')
        assert os.path.exists(outdir)

        cmd = f"python {script_full_path} --yacht_output {yacht_output} --sheet_name min_coverage0.2 --genome_to_taxid {genome_to_taxid} --outfile_prefix cami_result --outdir {outdir}"
        with self.assertRaises(subprocess.CalledProcessError):
            res = subprocess.run(cmd, shell=True, check=True)

    def test_wrong_outdir(self):
        script_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        script_dir = os.path.join(script_dir, 'srcs')
        script_full_path = os.path.join(script_dir, 'standardize_yacht_output.py')
        assert os.path.exists(script_full_path)

        yacht_output = os.path.join(os.path.dirname(__file__), 'testdata/standardize_output_testdata/result.xlsx')
        assert os.path.exists(yacht_output)

        genome_to_taxid = os.path.join(os.path.dirname(__file__), 'testdata/standardize_output_testdata/toy_genome_to_taxid.tsv')
        assert os.path.exists(genome_to_taxid)

        outdir = os.path.join(os.path.dirname(__file__), 'testdata_nonexisting')
        cmd = 'rm -rf ' + outdir
        try:
            subprocess.run(cmd, shell=True, check=True)
        except:
            pass
        assert not os.path.exists(outdir)

        cmd = f"python {script_full_path} --yacht_output {yacht_output} --sheet_name min_coverage0.2 --genome_to_taxid {genome_to_taxid} --outfile_prefix cami_result --outdir {outdir}"
        res = subprocess.run(cmd, shell=True, check=True)
        assert res.returncode == 0
        assert os.path.exists(outdir)

        cmd = 'rm -rf ' + outdir
        res = subprocess.run(cmd, shell=True, check=True)
        assert res.returncode == 0


if __name__ == '__main__':
    unittest.main()
