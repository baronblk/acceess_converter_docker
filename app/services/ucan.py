import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pandas as pd
import jaydebeapi
import glob

logger = logging.getLogger("accdb_web.ucan")

# UCanAccess Driver Class
DRIVER_CLASS = "net.ucanaccess.jdbc.UcanaccessDriver"


def _ucan_home() -> Path:
    """Get UCanAccess installation directory"""
    home = os.environ.get('UCANACCESS_HOME', '/opt/ucanaccess')
    return Path(home)


def _collect_ucan_jars() -> Tuple[List[str], List[str]]:
    """
    Collect all required UCanAccess JAR files.
    Returns: (found_jars, missing_jars)
    """
    ucan_home = _ucan_home()
    
    # Required JAR patterns
    required_patterns = [
        'lib/ucanaccess*.jar',
        'lib/hsqldb*.jar',
        'lib/jackcess-[0-9]*.jar',
        'lib/jackcess-encrypt*.jar',
        'lib/commons-lang*.jar',
        'lib/commons-logging*.jar'
    ]
    
    found_jars = []
    missing_jars = []
    
    logger.info(f"Searching for JAR files in: {ucan_home}")
    
    for pattern in required_patterns:
        # Build full pattern path
        jar_path = ucan_home / pattern
        logger.debug(f"Searching pattern: {jar_path}")
        
        # Find matching files
        matches = glob.glob(str(jar_path))
        
        if matches:
            found_jars.extend([str(Path(m).resolve()) for m in matches])
            logger.debug(f"Found JARs for pattern {pattern}: {matches}")
        else:
            missing_jars.append(str(jar_path))
            logger.warning(f"No JARs found for pattern: {pattern}")
    
    logger.info(f"JAR discovery: {len(found_jars)} found, {len(missing_jars)} missing")
    
    return found_jars, missing_jars


def _jdbc_url(db_path: Path) -> str:
    """Build JDBC connection URL for Access database"""
    # Use absolute path and disable memory mode for better compatibility
    abs_path = db_path.resolve()
    return f"jdbc:ucanaccess://{abs_path};memory=false"


def _ensure_file(db_path: Path) -> Path:
    """Ensure database file exists and is readable"""
    if not db_path.exists():
        raise FileNotFoundError(f"Database file not found: {db_path}")
    
    if not db_path.is_file():
        raise ValueError(f"Path is not a file: {db_path}")
    
    # Check if file is readable
    try:
        with open(db_path, 'rb') as f:
            # Read first few bytes to ensure file is accessible
            f.read(8)
    except Exception as e:
        raise PermissionError(f"Cannot read database file: {db_path}. Error: {e}")
    
    return db_path


def connect(db_path: Path):
    """
    Connect to Access database using UCanAccess with explicit JAR loading.
    
    Args:
        db_path: Path to the Access database file
        
    Returns:
        JDBC connection object
        
    Raises:
        Exception: If connection fails
    """
    try:
        # Validate database file
        db_path = _ensure_file(db_path)
        
        # Collect JAR files
        found_jars, missing_jars = _collect_ucan_jars()
        
        if missing_jars:
            logger.warning(f"Missing JAR files: {missing_jars}")
        
        if not found_jars:
            raise RuntimeError("No UCanAccess JAR files found")
        
        # Build JDBC URL
        jdbc_url = _jdbc_url(db_path)
        
        logger.info(f"Connecting to: {jdbc_url}")
        logger.debug(f"Using JAR files: {found_jars}")
        
        # Connect with explicit JAR loading
        conn = jaydebeapi.connect(
            DRIVER_CLASS,
            jdbc_url,
            [],  # No username/password for Access files
            jars=found_jars
        )
        
        logger.info("Successfully connected to Access database")
        return conn
        
    except Exception as e:
        logger.error(f"Connection failed: {e}")
        raise


def list_tables(db_path: Path) -> List[str]:
    """
    List all user tables in the Access database.
    
    Args:
        db_path: Path to the Access database file
        
    Returns:
        List of table names
    """
    try:
        db_path = Path(db_path)
        conn = connect(db_path)
        
        try:
            cursor = conn.cursor()
            
            # Get database metadata
            cursor.execute("""
                SELECT TABLE_NAME 
                FROM INFORMATION_SCHEMA.TABLES 
                WHERE TABLE_TYPE = 'TABLE' 
                AND TABLE_SCHEMA = 'PUBLIC'
                ORDER BY TABLE_NAME
            """)
            
            tables = [row[0] for row in cursor.fetchall()]
            
            # Filter out system tables
            user_tables = [
                table for table in tables 
                if not table.upper().startswith(('MSY', 'USY', '~TMP'))
            ]
            
            logger.info(f"Found {len(user_tables)} user tables in {db_path.name}")
            return user_tables
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Failed to list tables: {e}")
        raise


def read_table(db_path: Path, table_name: str) -> pd.DataFrame:
    """
    Read a table from the Access database as a pandas DataFrame.
    
    Args:
        db_path: Path to the Access database file
        table_name: Name of the table to read
        
    Returns:
        pandas DataFrame containing the table data
    """
    try:
        db_path = Path(db_path)
        conn = connect(db_path)
        
        try:
            # Use pandas to read the SQL query
            query = f'SELECT * FROM "{table_name}"'
            logger.info(f"Reading table: {table_name}")
            
            df = pd.read_sql_query(query, conn)
            
            logger.info(f"Read {len(df)} rows from table {table_name}")
            return df
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.error(f"Failed to read table {table_name}: {e}")
        raise


def diagnose_ucanaccess() -> Dict[str, Any]:
    """
    Run comprehensive UCanAccess diagnostics.
    
    Returns:
        Dictionary with diagnostic information
    """
    try:
        ucan_home = _ucan_home()
        found_jars, missing_jars = _collect_ucan_jars()
        
        # Test driver loading
        driver_available = False
        driver_error = "Not tested"
        
        try:
            if found_jars:
                # Try to connect to a dummy URL to test driver availability
                test_conn = jaydebeapi.connect(
                    DRIVER_CLASS,
                    "jdbc:ucanaccess://dummy.accdb;memory=false",
                    [],
                    jars=found_jars
                )
                test_conn.close()
                driver_available = True
        except Exception as e:
            driver_error = str(e)
            # Driver not loading is expected for dummy connection, 
            # but if we get a "No suitable driver" error, that's the real problem
            if "No suitable driver" not in str(e):
                driver_available = True  # Driver loads, just can't connect to dummy file
        
        diagnosis = {
            "UCANACCESS_HOME": str(ucan_home),
            "driver": DRIVER_CLASS,
            "driver_available": driver_available,
            "driver_error": driver_error,
            "jars_found": found_jars,
            "jars_missing": missing_jars,
            "ok": len(missing_jars) == 0 and driver_available,
            "jar_count": len(found_jars),
            "total_expected": 6  # Expected number of JAR patterns
        }
        
        logger.info(f"UCanAccess diagnosis: ok={diagnosis['ok']}, jars={len(found_jars)}")
        return diagnosis
        
    except Exception as e:
        logger.error(f"Diagnosis failed: {e}")
        return {
            "UCANACCESS_HOME": str(_ucan_home()),
            "driver": DRIVER_CLASS,
            "driver_available": False,
            "driver_error": str(e),
            "jars_found": [],
            "jars_missing": ["unknown"],
            "ok": False,
            "jar_count": 0,
            "total_expected": 6,
            "error": str(e)
        }


class AccessService:
    """Service for managing Access database operations using UCanAccess"""
    
    def __init__(self):
        self.current_connection = None
        
    def connect(self, access_file_path: str):
        """Connect to an Access database file"""
        return connect(Path(access_file_path))
        
    def list_tables(self, access_file_path: str) -> List[str]:
        """List all tables in the Access database"""
        return list_tables(Path(access_file_path))
        
    def read_table(self, access_file_path: str, table_name: str) -> pd.DataFrame:
        """Read a table from the Access database as DataFrame"""
        return read_table(Path(access_file_path), table_name)
        
    def get_tables(self, access_file_path: str) -> List[str]:
        """Alias for list_tables for backward compatibility"""
        return self.list_tables(access_file_path)
        
    def get_table_data(self, access_file_path: str, table_names: List[str]) -> Dict[str, pd.DataFrame]:
        """Get data for multiple tables"""
        result = {}
        for table_name in table_names:
            result[table_name] = self.read_table(access_file_path, table_name)
        return result
        
    def diagnose_ucanaccess(self) -> Dict[str, Any]:
        """Run UCanAccess diagnostics"""
        return diagnose_ucanaccess()
