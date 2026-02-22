"""
Calc tools — spreadsheet-specific tools via call_plugin().
Path is optional — omit it to use the active document.
"""

from typing import Any, Callable, Dict, Optional


def _p(params: Dict[str, Any], path: Optional[str]) -> Dict[str, Any]:
    """Add file_path only when a path was given."""
    if path is not None:
        params["file_path"] = path
    return params


def register(mcp, call_plugin: Callable[[str, Dict[str, Any]], Dict[str, Any]]):

    @mcp.tool()
    def read_spreadsheet_cells(range: str, path: Optional[str] = None,
                               sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """Read cell values from a Calc spreadsheet.

        Args:
            range: Cell range (e.g. 'A1:D10', 'B3'). Prefix with sheet
                   name and dot for a specific sheet (e.g. 'Sheet1.A1:D10').
            path: Absolute path to the spreadsheet (optional, uses active doc)
            sheet_name: Sheet name (optional, alternative to prefixing range)
        """
        actual_range = range
        if sheet_name and '.' not in range:
            actual_range = f"{sheet_name}.{range}"
        return call_plugin("read_cells", _p({
            "range_str": actual_range}, path))

    @mcp.tool()
    def write_spreadsheet_cell(cell: str, value: str,
                               path: Optional[str] = None,
                               sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """Write a value to a Calc spreadsheet cell.

        Args:
            cell: Cell address (e.g. 'B3'). Prefix with sheet name
                  for a specific sheet (e.g. 'Sheet1.B3').
            value: Value to write (numbers are auto-detected)
            path: Absolute path to the spreadsheet (optional, uses active doc)
            sheet_name: Sheet name (optional, alternative to prefixing cell)
        """
        actual_cell = cell
        if sheet_name and '.' not in cell:
            actual_cell = f"{sheet_name}.{cell}"
        return call_plugin("write_cell", _p({
            "cell": actual_cell, "value": value}, path))

    @mcp.tool()
    def list_spreadsheet_sheets(path: Optional[str] = None) -> Dict[str, Any]:
        """List all sheets in a Calc spreadsheet.

        Args:
            path: Absolute path to the spreadsheet (optional, uses active doc)
        """
        return call_plugin("list_sheets", _p({}, path))

    @mcp.tool()
    def get_spreadsheet_sheet_info(path: Optional[str] = None,
                                   sheet_name: Optional[str] = None) -> Dict[str, Any]:
        """Get info about a spreadsheet sheet (used range, dimensions).

        Args:
            path: Absolute path to the spreadsheet (optional, uses active doc)
            sheet_name: Sheet name (optional, defaults to active sheet)
        """
        params: Dict[str, Any] = {}
        if sheet_name is not None:
            params["sheet_name"] = sheet_name
        return call_plugin("get_sheet_info", _p(params, path))
