from __future__ import annotations
import os
import logging
from pathlib import Path
from typing import List, Dict, Any, Tuple
import pandas as pd
import jaydebeapi
import glob

from ..core.logging import get_logger

logger = get_logger("ucan")

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
        
        # Log database file details
        file_size_mb = os.path.getsize(db_path) / (1024 * 1024)
        logger.info(f"Database file: {db_path}")
        logger.info(f"File size: {file_size_mb:.2f}MB")
        logger.info(f"File exists: {os.path.exists(db_path)}")
        logger.info(f"File readable: {os.access(db_path, os.R_OK)}")
        
        # Collect JAR files
        found_jars, missing_jars = _collect_ucan_jars()
        
        if missing_jars:
            logger.warning(f"Missing JAR files: {missing_jars}")
        
        if not found_jars:
            logger.error("No UCanAccess JAR files found")
            raise RuntimeError("No UCanAccess JAR files found")
        
        logger.info(f"Found {len(found_jars)} JAR files")
        logger.debug(f"JAR files: {found_jars}")
        
        # Build JDBC URL
        jdbc_url = _jdbc_url(db_path)
        
        logger.info(f"JDBC URL: {jdbc_url}")
        logger.debug(f"Driver class: {DRIVER_CLASS}")
        
        # Connect with explicit JAR loading
        logger.debug("Attempting JDBC connection...")
        conn = jaydebeapi.connect(
            DRIVER_CLASS,
            jdbc_url,
            [],  # No username/password for Access files
            jars=found_jars
        )
        
        logger.info("JDBC connection established successfully")
        return conn
        
    except Exception as e:
        logger.exception(f"Failed to connect to database {db_path}: {str(e)}")
        raise


def _info_schema_tables(conn) -> List[str]:
    """
    Versuche Tabellen über INFORMATION_SCHEMA zu finden.
    
    Returns:
        Liste der Tabellennamen aus INFORMATION_SCHEMA
    """
    cursor = conn.cursor()
    names: List[str] = []
    
    # Versuche zuerst INFORMATION_SCHEMA.TABLES
    try:
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_TYPE 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_TYPE IN ('TABLE', 'VIEW')
            AND TABLE_SCHEMA = 'PUBLIC'
            ORDER BY TABLE_NAME
        """)
        rows = cursor.fetchall()
        for row in rows:
            name = str(row[0]) if row[0] else ""
            if name:
                names.append(name)
        logger.debug(f"Found {len(names)} tables via INFORMATION_SCHEMA.TABLES")
        return names
    except Exception as e:
        logger.debug(f"INFORMATION_SCHEMA.TABLES failed: {e}")
    
    # Fallback: INFORMATION_SCHEMA.SYSTEM_TABLES (ältere UCanAccess)
    try:
        cursor.execute("""
            SELECT TABLE_NAME, TABLE_TYPE 
            FROM INFORMATION_SCHEMA.SYSTEM_TABLES 
            WHERE TABLE_TYPE IN ('TABLE', 'VIEW')
            ORDER BY TABLE_NAME
        """)
        rows = cursor.fetchall()
        for row in rows:
            name = str(row[0]) if row[0] else ""
            if name:
                names.append(name)
        logger.debug(f"Found {len(names)} tables via INFORMATION_SCHEMA.SYSTEM_TABLES")
    except Exception as e:
        logger.debug(f"INFORMATION_SCHEMA.SYSTEM_TABLES failed: {e}")
    
    return names


def _metadata_tables(conn) -> List[Tuple[str, str]]:
    """
    Nutzt JDBC DatabaseMetaData.getTables() über jaydebeapi.
    
    Returns:
        Liste von (table_name, table_type) Tupeln
    """
    names: List[Tuple[str, str]] = []
    
    try:
        # Zugriff auf die Java-Connection für JDBC-Metadaten
        jconn = conn.jconn  # jaydebeapi Java-Connection
        metadata = jconn.getMetaData()
        
        # Hole alle Tabellen-Typen
        table_types = ["TABLE", "SYSTEM TABLE", "VIEW", "ALIAS", "SYNONYM"]
        result_set = metadata.getTables(None, None, "%", table_types)
        
        while result_set.next():
            table_name = result_set.getString(3)  # TABLE_NAME (Spalte 3)
            table_type = result_set.getString(4)  # TABLE_TYPE (Spalte 4)
            
            if table_name:
                names.append((str(table_name), str(table_type) if table_type else "UNKNOWN"))
        
        result_set.close()
        logger.debug(f"Found {len(names)} tables via JDBC metadata")
        
    except Exception as e:
        logger.warning(f"JDBC metadata getTables() failed: {e}")
    
    return names


def list_tables_detailed(db_path: Path) -> List[Dict[str, str]]:
    """
    Liefert detaillierte Liste inkl. Quelle (info_schema|metadata) und Typ.
    
    Args:
        db_path: Path to the Access database file
        
    Returns:
        Liste von Dictionaries mit name, type, source
    """
    db_path = Path(db_path).resolve()
    logger.info(f"Starting table discovery for: {db_path}")
    
    conn = connect(db_path)
    
    try:
        # Schritt A: Versuche INFORMATION_SCHEMA
        logger.debug("Attempting INFORMATION_SCHEMA table discovery...")
        info_tables = _info_schema_tables(conn)
        info_filtered = [name for name in info_tables if not name.upper().startswith("MSYS")]
        info_set = set(info_filtered)
        
        logger.info(f"INFORMATION_SCHEMA: found {len(info_tables)} total, {len(info_filtered)} after filtering")
        if info_filtered:
            sample_tables = info_filtered[:5]
            logger.debug(f"INFORMATION_SCHEMA sample tables: {sample_tables}")
        
        # Schritt B: Fallback mit JDBC Metadata
        logger.debug("Attempting JDBC Metadata table discovery...")
        meta_pairs = _metadata_tables(conn)
        meta_filtered = [(name, table_type) for (name, table_type) in meta_pairs 
                        if not name.upper().startswith("MSYS")]
        
        logger.info(f"JDBC Metadata: found {len(meta_pairs)} total, {len(meta_filtered)} after filtering")
        if meta_filtered:
            sample_meta = [(name, ttype) for name, ttype in meta_filtered[:5]]
            logger.debug(f"JDBC Metadata sample tables: {sample_meta}")
        
        info_count = len(info_filtered)
        metadata_count = len(meta_filtered)
        
        logger.info(f"Table discovery summary: info_schema={info_count}, metadata={metadata_count}")
        
        # Kombiniere Ergebnisse
        detailed_tables: List[Dict[str, str]] = []
        
        # Füge INFORMATION_SCHEMA Tabellen hinzu
        for name in sorted(info_set):
            detailed_tables.append({
                "name": name,
                "type": "TABLE",  # INFORMATION_SCHEMA hat oft keinen spezifischen Typ
                "source": "info_schema"
            })
        
        # Füge Metadata-Tabellen hinzu (nur wenn nicht schon in info_schema vorhanden)
        for name, table_type in meta_filtered:
            if name not in info_set:
                detailed_tables.append({
                    "name": name,
                    "type": table_type or "UNKNOWN",
                    "source": "metadata"
                })
        
        final_count = len(detailed_tables)
        logger.info(f"Final result: {final_count} unique tables found")
        
        if final_count == 0:
            logger.warning(
                f"No tables found in {db_path.name}! "
                "Possible causes: corrupted database, linked tables, permissions issues, or unsupported format. "
                "Try /diagnostics/tables endpoint for detailed analysis."
            )
        else:
            # Log sample of found tables
            sample_names = [t["name"] for t in detailed_tables[:5]]
            logger.info(f"Sample tables: {sample_names}")
        
        return detailed_tables
        
    except Exception as e:
        logger.exception(f"Table discovery failed for {db_path}: {str(e)}")
        raise
        
    finally:
        conn.close()


def list_tables(db_path: Path) -> List[str]:
    """
    Kompakte Liste der Tabellen (Systemtabellen MSYS* ausgeschlossen).
    Nutzt zuerst INFORMATION_SCHEMA, dann Metadaten-Fallback.
    
    Args:
        db_path: Path to the Access database file
        
    Returns:
        List of table names
    """
    try:
        detailed_tables = list_tables_detailed(db_path)
        unique_names = sorted({table["name"] for table in detailed_tables})
        
        logger.info(f"Found {len(unique_names)} user tables in {db_path.name}")
        return unique_names
        
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
        logger.info(f"Reading table '{table_name}' from {db_path}")
        
        conn = connect(db_path)
        
        try:
            # Use pandas to read the SQL query
            query = f'SELECT * FROM "{table_name}"'
            logger.debug(f"Executing query: {query}")
            
            df = pd.read_sql_query(query, conn)
            
            # Log detailed table info
            row_count = len(df)
            col_count = len(df.columns)
            logger.info(f"Table '{table_name}': {row_count} rows, {col_count} columns")
            
            if col_count > 0:
                column_names = list(df.columns)[:10]  # First 10 columns
                logger.debug(f"Columns: {column_names}")
                
            if row_count > 0:
                # Log sample data types and memory usage
                memory_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
                logger.debug(f"Memory usage: {memory_mb:.2f}MB")
            
            return df
            
        finally:
            conn.close()
            
    except Exception as e:
        logger.exception(f"Failed to read table '{table_name}' from {db_path}: {str(e)}")
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
