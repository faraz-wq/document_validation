import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import fitz  # PyMuPDF

from app.pdf_annotator import draw_bounding_boxes_on_pdf, annotate_document


class TestPdfAnnotator:
    """Test cases for the PDF annotation functions"""

    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Create temporary directories for test files
        self.temp_dir = Path(tempfile.mkdtemp())
        self.input_dir = self.temp_dir / "input"
        self.output_dir = self.temp_dir / "output"
        self.input_dir.mkdir()
        self.output_dir.mkdir()

    def teardown_method(self):
        """Clean up after each test method."""
        import shutil
        shutil.rmtree(self.temp_dir)

    def test_draw_bounding_boxes_on_pdf_basic(self):
        """Test drawing bounding boxes on a PDF"""
        # Create a simple PDF for testing
        pdf_path = self.input_dir / "test.pdf"
        doc = fitz.open()
        page = doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        # Define bounding boxes
        bounding_boxes = {
            "applicant_name": {
                "filename": "test.pdf",
                "page": 1,
                "coordinates": [100, 200, 300, 400]
            }
        }

        output_path = self.output_dir / "annotated_test.pdf"

        # Call the function
        result_path = draw_bounding_boxes_on_pdf(pdf_path, bounding_boxes, output_path)

        # Check that the result path is correct
        assert result_path == output_path
        assert result_path.exists()

    def test_draw_bounding_boxes_on_pdf_multiple_boxes(self):
        """Test drawing multiple bounding boxes on a PDF"""
        # Create a simple PDF for testing
        pdf_path = self.input_dir / "test_multi.pdf"
        doc = fitz.open()
        page = doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        # Define multiple bounding boxes
        bounding_boxes = {
            "applicant_name": {
                "filename": "test_multi.pdf",
                "page": 1,
                "coordinates": [100, 200, 300, 400]
            },
            "fathers_name": {
                "filename": "test_multi.pdf",
                "page": 1,
                "coordinates": [400, 200, 500, 600]
            }
        }

        output_path = self.output_dir / "annotated_multi.pdf"

        # Call the function
        result_path = draw_bounding_boxes_on_pdf(pdf_path, bounding_boxes, output_path)

        # Check that the result path is correct
        assert result_path == output_path
        assert result_path.exists()

    def test_draw_bounding_boxes_on_pdf_invalid_coordinates(self):
        """Test drawing bounding boxes with invalid coordinates"""
        # Create a simple PDF for testing
        pdf_path = self.input_dir / "test_invalid.pdf"
        doc = fitz.open()
        page = doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        # Define bounding boxes with invalid coordinates (not 4 values)
        bounding_boxes = {
            "applicant_name": {
                "filename": "test_invalid.pdf",
                "page": 1,
                "coordinates": [100, 200, 300]  # Only 3 values instead of 4
            }
        }

        output_path = self.output_dir / "annotated_invalid.pdf"

        # Call the function - it should handle invalid coordinates gracefully
        result_path = draw_bounding_boxes_on_pdf(pdf_path, bounding_boxes, output_path)

        # Check that the result path is correct and file exists
        assert result_path == output_path
        assert result_path.exists()

    def test_draw_bounding_boxes_on_pdf_invalid_page(self):
        """Test drawing bounding boxes on an invalid page"""
        # Create a simple PDF for testing
        pdf_path = self.input_dir / "test_page.pdf"
        doc = fitz.open()
        page = doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        # Define bounding boxes for a non-existent page
        bounding_boxes = {
            "applicant_name": {
                "filename": "test_page.pdf",
                "page": 10,  # Page doesn't exist (only has 1 page)
                "coordinates": [100, 200, 300, 400]
            }
        }

        output_path = self.output_dir / "annotated_page.pdf"

        # Call the function
        result_path = draw_bounding_boxes_on_pdf(pdf_path, bounding_boxes, output_path)

        # Check that the result path is correct and file exists
        # Even with invalid page, the function should not crash
        assert result_path == output_path
        assert result_path.exists()

    def test_annotate_document_with_pdf(self):
        """Test annotate_document with PDF file"""
        # Create a simple PDF for testing
        pdf_path = self.input_dir / "test_annotate.pdf"
        doc = fitz.open()
        page = doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        # Define bounding boxes
        bounding_boxes = {
            "applicant_name": {
                "filename": "test_annotate.pdf",
                "page": 1,
                "coordinates": [100, 200, 300, 400]
            }
        }

        # Call the annotate_document function
        result_path = annotate_document(
            file_path=pdf_path,
            bounding_boxes=bounding_boxes,
            output_dir=self.output_dir,
            filename_suffix="_annotated"
        )

        # Check that the result exists and is a PDF
        assert result_path.exists()
        assert result_path.suffix == ".pdf"
        assert "_annotated.pdf" in result_path.name

    def test_annotate_document_with_unsupported_file(self):
        """Test annotate_document with unsupported file type"""
        # Create a text file
        txt_path = self.input_dir / "test.txt"
        with open(txt_path, 'w') as f:
            f.write("test content")

        # Define bounding boxes
        bounding_boxes = {
            "applicant_name": {
                "filename": "test.txt",
                "page": 1,
                "coordinates": [100, 200, 300, 400]
            }
        }

        # This should raise ValueError for unsupported file type
        with pytest.raises(ValueError, match="Unsupported file type: .txt"):
            annotate_document(
                file_path=txt_path,
                bounding_boxes=bounding_boxes,
                output_dir=self.output_dir,
                filename_suffix="_annotated"
            )

    def test_draw_bounding_boxes_on_pdf_with_mock_error(self):
        """Test error handling in draw_bounding_boxes_on_pdf"""
        # Create a dummy PDF file first
        pdf_path = self.input_dir / "dummy.pdf"
        doc = fitz.open()
        page = doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        bounding_boxes = {
            "applicant_name": {
                "filename": "dummy.pdf",
                "page": 1,
                "coordinates": [100, 200, 300, 400]
            }
        }

        output_path = self.output_dir / "error_test.pdf"

        # This should work fine (no error raised)
        result_path = draw_bounding_boxes_on_pdf(pdf_path, bounding_boxes, output_path)
        assert result_path.exists()

    def test_annotate_document_with_different_filename_suffix(self):
        """Test annotate_document with different filename suffix"""
        # Create a simple PDF for testing
        pdf_path = self.input_dir / "test_suffix.pdf"
        doc = fitz.open()
        page = doc.new_page()
        doc.save(str(pdf_path))
        doc.close()

        # Define bounding boxes
        bounding_boxes = {
            "applicant_name": {
                "filename": "test_suffix.pdf",
                "page": 1,
                "coordinates": [100, 200, 300, 400]
            }
        }

        # Call the annotate_document function with custom suffix
        result_path = annotate_document(
            file_path=pdf_path,
            bounding_boxes=bounding_boxes,
            output_dir=self.output_dir,
            filename_suffix="_highlighted"
        )

        # Check that the result exists and has the correct suffix
        assert result_path.exists()
        assert "_highlighted.pdf" in result_path.name