"""
Data Persistence Manager
Ensures all processing outputs, metadata, and logs are persisted to storage
"""

import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict

from config import Config

logger = logging.getLogger(__name__)


@dataclass
class ProcessingManifest:
    """Manifest tracking all persisted data for a processing session"""
    session_id: str
    session_start: str
    session_end: Optional[str] = None
    certificate_type: Optional[str] = None

    # Input files
    input_files: List[str] = None
    total_files: int = 0

    # Stage 1 outputs
    stage1_outputs: List[str] = None
    stage1_success_count: int = 0
    stage1_failed_count: int = 0

    # Stage 2 outputs
    stage2_output: Optional[str] = None
    stage2_success: bool = False

    # Metadata files
    metadata_files: List[str] = None

    # Log files
    log_files: List[str] = None

    # Evaluation outputs (if applicable)
    evaluation_outputs: List[str] = None

    # PDF analysis outputs (if applicable)
    pdf_analysis_outputs: List[str] = None

    def __post_init__(self):
        """Initialize mutable defaults"""
        if self.input_files is None:
            self.input_files = []
        if self.stage1_outputs is None:
            self.stage1_outputs = []
        if self.metadata_files is None:
            self.metadata_files = []
        if self.log_files is None:
            self.log_files = []
        if self.evaluation_outputs is None:
            self.evaluation_outputs = []
        if self.pdf_analysis_outputs is None:
            self.pdf_analysis_outputs = []

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        return asdict(self)

    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), indent=2)


class PersistenceManager:
    """Manages persistence of all processing outputs and metadata"""

    def __init__(self, session_id: Optional[str] = None):
        """
        Initialize persistence manager

        Args:
            session_id: Unique session identifier (auto-generated if not provided)
        """
        self.session_id = session_id or self._generate_session_id()
        self.manifest = ProcessingManifest(
            session_id=self.session_id,
            session_start=datetime.now().isoformat()
        )

        # Create session directory
        self.session_dir = Config.OUTPUTS_DIR / f"session_{self.session_id}"
        self.session_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Persistence Manager initialized: session_{self.session_id}")
        logger.info(f"Session directory: {self.session_dir}")

    @staticmethod
    def _generate_session_id() -> str:
        """Generate unique session ID"""
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    def register_input_file(self, file_path: Path) -> None:
        """
        Register an input file

        Args:
            file_path: Path to input file
        """
        self.manifest.input_files.append(str(file_path.absolute()))
        self.manifest.total_files += 1
        logger.debug(f"Registered input file: {file_path.name}")

    def register_stage1_output(
        self,
        text_file: Path,
        metadata_file: Path,
        success: bool
    ) -> None:
        """
        Register Stage 1 output files

        Args:
            text_file: Path to extracted text file
            metadata_file: Path to metadata JSON file
            success: Whether extraction was successful
        """
        if success:
            self.manifest.stage1_outputs.append(str(text_file.absolute()))
            self.manifest.metadata_files.append(str(metadata_file.absolute()))
            self.manifest.stage1_success_count += 1
            logger.debug(f"Registered Stage 1 success: {text_file.name}")
        else:
            self.manifest.stage1_failed_count += 1
            logger.debug(f"Registered Stage 1 failure")

    def register_stage2_output(
        self,
        summary_file: Path,
        metadata_file: Path,
        success: bool
    ) -> None:
        """
        Register Stage 2 output files

        Args:
            summary_file: Path to summary markdown file
            metadata_file: Path to metadata JSON file
            success: Whether summary generation was successful
        """
        if success:
            self.manifest.stage2_output = str(summary_file.absolute())
            self.manifest.metadata_files.append(str(metadata_file.absolute()))
            self.manifest.stage2_success = True
            logger.debug(f"Registered Stage 2 success: {summary_file.name}")
        else:
            self.manifest.stage2_success = False
            logger.debug(f"Registered Stage 2 failure")

    def register_log_file(self, log_file: Path) -> None:
        """
        Register a log file

        Args:
            log_file: Path to log file
        """
        self.manifest.log_files.append(str(log_file.absolute()))
        logger.debug(f"Registered log file: {log_file.name}")

    def register_evaluation_output(self, eval_file: Path) -> None:
        """
        Register an evaluation output file

        Args:
            eval_file: Path to evaluation output file
        """
        self.manifest.evaluation_outputs.append(str(eval_file.absolute()))
        logger.debug(f"Registered evaluation output: {eval_file.name}")

    def register_pdf_analysis(self, analysis_file: Path) -> None:
        """
        Register a PDF analysis output file

        Args:
            analysis_file: Path to PDF analysis file
        """
        self.manifest.pdf_analysis_outputs.append(str(analysis_file.absolute()))
        logger.debug(f"Registered PDF analysis: {analysis_file.name}")

    def save_manifest(self, finalize: bool = False) -> Path:
        """
        Save processing manifest to file

        Args:
            finalize: Whether to finalize the manifest (add end time)

        Returns:
            Path to saved manifest file
        """
        if finalize:
            self.manifest.session_end = datetime.now().isoformat()

        manifest_file = self.session_dir / "manifest.json"
        with open(manifest_file, 'w', encoding='utf-8') as f:
            f.write(self.manifest.to_json())

        logger.info(f"Manifest saved: {manifest_file}")
        return manifest_file

    def generate_session_summary(self) -> str:
        """
        Generate human-readable session summary

        Returns:
            Formatted summary string
        """
        lines = []
        lines.append("=" * 80)
        lines.append(f"PROCESSING SESSION SUMMARY: {self.session_id}".center(80))
        lines.append("=" * 80)
        lines.append(f"\nStart Time: {self.manifest.session_start}")
        if self.manifest.session_end:
            lines.append(f"End Time: {self.manifest.session_end}")

        if self.manifest.certificate_type:
            lines.append(f"Certificate Type: {self.manifest.certificate_type}")

        lines.append(f"\n{'INPUT FILES':-^80}")
        lines.append(f"Total Files: {self.manifest.total_files}")
        for idx, file_path in enumerate(self.manifest.input_files, 1):
            lines.append(f"  {idx}. {Path(file_path).name}")

        lines.append(f"\n{'STAGE 1: DOCUMENT EXTRACTION':-^80}")
        lines.append(f"Successful: {self.manifest.stage1_success_count}")
        lines.append(f"Failed: {self.manifest.stage1_failed_count}")
        lines.append(f"Output Files: {len(self.manifest.stage1_outputs)}")

        lines.append(f"\n{'STAGE 2: SUMMARY GENERATION':-^80}")
        lines.append(f"Status: {'Success' if self.manifest.stage2_success else 'Failed'}")
        if self.manifest.stage2_output:
            lines.append(f"Output: {Path(self.manifest.stage2_output).name}")

        lines.append(f"\n{'METADATA & LOGS':-^80}")
        lines.append(f"Metadata Files: {len(self.manifest.metadata_files)}")
        lines.append(f"Log Files: {len(self.manifest.log_files)}")

        if self.manifest.evaluation_outputs:
            lines.append(f"\n{'EVALUATION OUTPUTS':-^80}")
            lines.append(f"Files: {len(self.manifest.evaluation_outputs)}")
            for file_path in self.manifest.evaluation_outputs:
                lines.append(f"  • {Path(file_path).name}")

        if self.manifest.pdf_analysis_outputs:
            lines.append(f"\n{'PDF ANALYSIS OUTPUTS':-^80}")
            lines.append(f"Files: {len(self.manifest.pdf_analysis_outputs)}")
            for file_path in self.manifest.pdf_analysis_outputs:
                lines.append(f"  • {Path(file_path).name}")

        lines.append(f"\n{'STORAGE LOCATION':-^80}")
        lines.append(f"Session Directory: {self.session_dir}")
        lines.append(f"Manifest File: {self.session_dir / 'manifest.json'}")

        lines.append("\n" + "=" * 80)

        return "\n".join(lines)

    def save_session_summary(self) -> Path:
        """
        Save session summary to file

        Returns:
            Path to saved summary file
        """
        summary = self.generate_session_summary()
        summary_file = self.session_dir / "session_summary.txt"

        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write(summary)

        logger.info(f"Session summary saved: {summary_file}")
        return summary_file

    def finalize_session(self) -> None:
        """Finalize the processing session"""
        self.save_manifest(finalize=True)
        summary_file = self.save_session_summary()

        logger.info("=" * 80)
        logger.info(f"SESSION FINALIZED: {self.session_id}")
        logger.info(f"All outputs saved to: {self.session_dir}")
        logger.info(f"Manifest: {self.session_dir / 'manifest.json'}")
        logger.info(f"Summary: {summary_file}")
        logger.info("=" * 80)

        # Print summary to console
        print("\n" + self.generate_session_summary())


def create_backup(source_dir: Path, backup_dir: Optional[Path] = None) -> Path:
    """
    Create backup of outputs directory

    Args:
        source_dir: Directory to backup
        backup_dir: Backup destination (auto-generated if not provided)

    Returns:
        Path to backup directory
    """
    import shutil

    if backup_dir is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_dir = Config.BASE_DIR / f"backups/backup_{timestamp}"

    backup_dir.mkdir(parents=True, exist_ok=True)

    logger.info(f"Creating backup: {source_dir} -> {backup_dir}")
    shutil.copytree(source_dir, backup_dir / source_dir.name, dirs_exist_ok=True)

    logger.info(f"Backup complete: {backup_dir}")
    return backup_dir


def list_sessions(outputs_dir: Optional[Path] = None) -> List[Dict]:
    """
    List all processing sessions

    Args:
        outputs_dir: Outputs directory to search (uses Config.OUTPUTS_DIR if not provided)

    Returns:
        List of session information dictionaries
    """
    outputs_dir = outputs_dir or Config.OUTPUTS_DIR

    sessions = []
    for session_dir in outputs_dir.glob("session_*"):
        manifest_file = session_dir / "manifest.json"
        if manifest_file.exists():
            with open(manifest_file, 'r', encoding='utf-8') as f:
                manifest = json.load(f)
                sessions.append({
                    "session_id": manifest["session_id"],
                    "session_dir": str(session_dir),
                    "start_time": manifest["session_start"],
                    "end_time": manifest.get("session_end"),
                    "total_files": manifest["total_files"],
                    "stage1_success": manifest["stage1_success_count"],
                    "stage2_success": manifest["stage2_success"]
                })

    # Sort by start time (newest first)
    sessions.sort(key=lambda x: x["start_time"], reverse=True)

    return sessions


def print_sessions_list():
    """Print list of all processing sessions"""
    sessions = list_sessions()

    if not sessions:
        print("No processing sessions found.")
        return

    print("\n" + "=" * 80)
    print("PROCESSING SESSIONS")
    print("=" * 80)

    for idx, session in enumerate(sessions, 1):
        print(f"\n{idx}. Session: {session['session_id']}")
        print(f"   Start: {session['start_time']}")
        if session['end_time']:
            print(f"   End: {session['end_time']}")
        print(f"   Files: {session['total_files']}")
        print(f"   Stage 1 Success: {session['stage1_success']}")
        print(f"   Stage 2 Success: {'Yes' if session['stage2_success'] else 'No'}")
        print(f"   Location: {session['session_dir']}")

    print("\n" + "=" * 80)


if __name__ == "__main__":
    # CLI for listing sessions
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "list":
        print_sessions_list()
    else:
        print("Usage: python persistence_manager.py list")
