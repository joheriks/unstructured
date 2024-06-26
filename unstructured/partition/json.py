"""Provides `partition_json()`.

Note this does not partition arbitrary JSON. Its only use-case is to "rehydrate" unstructured
document elements serialized to JSON, essentially the same function as `elements_from_json()`, but
this allows a document of already-partitioned elements to be combined transparently with other
documents in a partitioning run. It also allows multiple (low-cost) chunking runs to be performed on
a document while only incurring partitioning cost once.
"""

from __future__ import annotations

import json
from typing import IO, Any, Optional

from unstructured.chunking import add_chunking_strategy
from unstructured.documents.elements import Element, process_metadata
from unstructured.file_utils.filetype import (
    FileType,
    add_metadata_with_filetype,
    is_json_processable,
)
from unstructured.partition.common import (
    exactly_one,
    get_last_modified_date,
    get_last_modified_date_from_file,
)
from unstructured.staging.base import dict_to_elements


@process_metadata()
@add_metadata_with_filetype(FileType.JSON)
@add_chunking_strategy
def partition_json(
    filename: Optional[str] = None,
    file: Optional[IO[bytes]] = None,
    text: Optional[str] = None,
    include_metadata: bool = True,
    metadata_filename: Optional[str] = None,
    metadata_last_modified: Optional[str] = None,
    date_from_file_object: bool = False,
    **kwargs: Any,
) -> list[Element]:
    """Partitions serialized Unstructured output into its constituent elements.

    Parameters
    ----------
    filename
        A string defining the target filename path.
    file
        A file-like object as bytes --> open(filename, "rb").
    text
        The string representation of the .json document.
    metadata_last_modified
        The last modified date for the document.
    date_from_file_object
        Applies only when providing file via `file` parameter. If this option is True, attempt
        infer last_modified metadata from bytes, otherwise set it to None.
    """
    if text is not None and text.strip() == "" and not file and not filename:
        return []

    exactly_one(filename=filename, file=file, text=text)

    last_modification_date = None
    file_text = ""
    if filename is not None:
        last_modification_date = get_last_modified_date(filename)
        with open(filename, encoding="utf8") as f:
            file_text = f.read()

    elif file is not None:
        last_modification_date = (
            get_last_modified_date_from_file(file) if date_from_file_object else None
        )

        file_content = file.read()
        file_text = file_content if isinstance(file_content, str) else file_content.decode()
        file.seek(0)

    elif text is not None:
        file_text = str(text)

    if not is_json_processable(file_text=file_text):
        raise ValueError(
            "JSON cannot be partitioned. Schema does not match the Unstructured schema.",
        )

    try:
        dict = json.loads(file_text)
        elements = dict_to_elements(dict)
    except json.JSONDecodeError:
        raise ValueError("Not a valid json")

    for element in elements:
        if include_metadata:
            element.metadata.last_modified = metadata_last_modified or last_modification_date
    # NOTE(Nathan): in future PR, try extracting items that look like text
    #               if file_text is a valid json but not an unstructured json

    return elements
