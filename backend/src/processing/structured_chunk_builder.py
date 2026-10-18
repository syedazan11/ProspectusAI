from typing import Any

class StructuredChunkBuilder:
    """
    Converts structured records into
    retrieval chunks.
    """

    def build(
        self,
        *,
        record_results: dict[str, Any],
    ) -> dict[str, list]:

        # parent_chunks: list[ParentChunk] = []
        # child_chunks: list[ChildChunk] = []

        # text_splitter = (
        #     RecursiveCharacterTextSplitter(
        #         chunk_size=800,
        #         chunk_overlap=150,
        #         separators=[
        #             "\n\n",
        #             "\n",
        #             ". ",
        #             " ",
        #             "",
        #         ],
        #     )
        # )

        # for index, (
        #     record_type,
        #     record,
        # ) in enumerate(
        #     self._all_records(
        #         record_results
        #     )
        # ):

        #     parent = self._parent_chunk(
        #         record_type=record_type,
        #         record=record,
        #         index=index,
        #     )

        #     parent_chunks.append(
        #         parent
        #     )

        #     child_chunks.extend(
        #         self._child_chunks(
        #             parent_chunk=parent,
        #             text_splitter=text_splitter,
        #         )
        #     )

        # return {
        #     "parent_chunks": parent_chunks,
        #     "child_chunks": child_chunks,
        # }
        chunks = []

        for index, (record_type, record) in enumerate(
            self._all_records(record_results)
        ):
            chunks.append(
                self._chunk(
                    record_type=record_type,
                    record=record,
                    index=index,
                )
            )

        return {
            "chunks": chunks,
        }

    def _all_records(
        self,
        record_results: dict[str, Any],
    ) -> list[tuple[str, Any]]:

        records: list[tuple[str, Any]] = []

        for record_type, values in (
            record_results.items()
        ):

            if not isinstance(
                values,
                list,
            ):
                continue

            for record in values:

                records.append(
                    (
                        record_type,
                        record,
                    )
                )

        return records
    
    def _record_text(
        self,
        record: Any,
    ) -> str:

        record_type = (
            record.__class__.__name__
            .replace("Record", "")
        )

        if record_type == "Person":
            return self._person_text(record)

        if record_type == "Admission":
            return self._admission_text(record)

        if record_type == "Academic":
            return self._academic_text(record)

        if record_type == "Fee":
            return self._fee_text(record)

        if record_type == "Research":
            return self._research_text(record)

        if record_type == "StudentLife":
            return self._student_life_text(record)

        if record_type == "Governance":
            return self._governance_text(record)

        if record_type == "Contact":
            return self._contact_text(record)

        if record_type == "AdmissionCategory":
            return self._admission_category_text(record)

        # Generic fallback
        lines: list[str] = []

        lines.append(
            f"Record Type: {record_type}"
        )

        lines.append("")
        

        if hasattr(
            record,
            "model_dump",
        ):
            items = record.model_dump().items()

        elif hasattr(
            record,
            "__dict__",
        ):
            items = record.__dict__.items()

        elif hasattr(
            record,
            "to_dict",
        ):
            items = record.to_dict().items()

        else:
            items = []

        for key, value in items:

            if value is None:
                continue

            if value == "":
                continue

            if value == {}:
                continue

            if value == []:
                continue

            if isinstance(
                value,
                dict,
            ):

                label = (
                    key.replace("_", " ")
                    .title()
                )

                lines.append(f"{label}:")

                for k, v in value.items():

                    item = (
                        k.replace("_", " ")
                        .title()
                    )

                    lines.append(
                        f"- {item}: {v}"
                    )

                lines.append("")

                continue

            if isinstance(
                value,
                list,
            ):

                label = (
                    key.replace("_", " ")
                    .title()
                )

                lines.append(f"{label}:")

                for item in value:
                    lines.append(f"- {item}")

                lines.append("")
                continue

            label = (
                key.replace("_", " ")
                .title()
            )

            lines.append(f"{label}:")
            lines.append(str(value))
            lines.append("")

        return "\n".join(lines)
    
    def _person_text(
        self,
        record: Any,
    ) -> str:

        lines: list[str] = []

        lines.append(
            "Record Type: Person"
        )
        lines.append("")

        if getattr(
            record,
            "name",
            None,
        ):
            lines.append("Name:")
            lines.append(record.name)
            lines.append("")

        if getattr(
            record,
            "role",
            None,
        ):
            lines.append("Role:")
            lines.append(record.role)
            lines.append("")

        if getattr(
            record,
            "department",
            None,
        ):
            lines.append("Department:")
            lines.append(record.department)
            lines.append("")

        qualifications = getattr(
            record,
            "qualifications",
            None,
        )

        if qualifications:

            lines.append(
                "Qualifications:"
            )

            if isinstance(
                qualifications,
                list,
            ):

                for qualification in qualifications:
                    lines.append(
                        f"- {qualification}"
                    )

            else:
                lines.append(
                    str(qualifications)
                )

            lines.append("")

        if getattr(
            record,
            "source_text",
            None,
        ):
            lines.append(
                "Details:"
            )
            lines.append(
                record.source_text
            )
            lines.append("")

        if getattr(
            record,
            "source_heading",
            None,
        ):
            lines.append(
                "Source Heading:"
            )
            lines.append(
                record.source_heading
            )
            lines.append("")

        if getattr(
            record,
            "source_page",
            None,
        ):
            lines.append(
                "Source Page:"
            )
            lines.append(
                str(record.source_page)
            )

        return "\n".join(lines)
    
    def _admission_text(
        self,
        record: Any,
    ) -> str:

        lines: list[str] = []

        lines.append(
            "Record Type: Admission"
        )
        lines.append("")

        if getattr(
            record,
            "title",
            None,
        ):
            lines.append("Title:")
            lines.append(record.title)
            lines.append("")

        if getattr(
            record,
            "category",
            None,
        ):
            lines.append("Category:")
            lines.append(record.category)
            lines.append("")

        details = getattr(
            record,
            "details",
            {},
        )

        if details:

            lines.append(
                "Admission Information:"
            )

            for key, value in (
                details.items()
            ):

                label = (
                    key.replace(
                        "_",
                        " ",
                    )
                    .title()
                )

                lines.append(
                    f"- {label}: {value}"
                )

            lines.append("")

        if getattr(
            record,
            "source_text",
            None,
        ):
            lines.append(
                "Details:"
            )
            lines.append(
                record.source_text
            )
            lines.append("")

        if getattr(
            record,
            "source_heading",
            None,
        ):
            lines.append(
                "Source Heading:"
            )
            lines.append(
                record.source_heading
            )
            lines.append("")

        if getattr(
            record,
            "source_page",
            None,
        ):
            lines.append(
                "Source Page:"
            )
            lines.append(
                str(record.source_page)
            )

        return "\n".join(lines)
    
    def _academic_text(
        self,
        record: Any,
    ) -> str:

        lines: list[str] = []

        lines.append(
            "Record Type: Academic"
        )
        lines.append("")

        if getattr(
            record,
            "title",
            None,
        ):
            lines.append("Programme:")
            lines.append(record.title)
            lines.append("")

        if getattr(
            record,
            "department",
            None,
        ):
            lines.append("Department:")
            lines.append(record.department)
            lines.append("")

        attributes = getattr(
            record,
            "attributes",
            {},
        )

        if attributes:

            lines.append(
                "Programme Information:"
            )

            for key, value in (
                attributes.items()
            ):

                label = (
                    key.replace(
                        "_",
                        " ",
                    )
                    .title()
                )

                lines.append(
                    f"- {label}: {value}"
                )

            lines.append("")

        if getattr(
            record,
            "source_text",
            None,
        ):
            lines.append(
                "Details:"
            )
            lines.append(
                record.source_text
            )
            lines.append("")

        if getattr(
            record,
            "source_heading",
            None,
        ):
            lines.append(
                "Source Heading:"
            )
            lines.append(
                record.source_heading
            )
            lines.append("")

        if getattr(
            record,
            "source_page",
            None,
        ):
            lines.append(
                "Source Page:"
            )
            lines.append(
                str(record.source_page)
            )

        return "\n".join(lines)
    
    def _fee_text(
        self,
        record: Any,
    ) -> str:

        lines: list[str] = []

        lines.append(
            "Record Type: Fee"
        )
        lines.append("")

        if getattr(
            record,
            "category",
            None,
        ):
            lines.append("Category:")
            lines.append(record.category)
            lines.append("")

        if getattr(
            record,
            "amount",
            None,
        ) is not None:

            lines.append("Amount:")
            lines.append(
                str(record.amount)
            )
            lines.append("")

        if getattr(
            record,
            "currency",
            None,
        ):
            lines.append("Currency:")
            lines.append(
                record.currency
            )
            lines.append("")

        if getattr(
            record,
            "payment_period",
            None,
        ):
            lines.append(
                "Payment Period:"
            )
            lines.append(
                record.payment_period
            )
            lines.append("")

        if getattr(
            record,
            "applicability",
            None,
        ):
            lines.append(
                "Applicability:"
            )
            lines.append(
                record.applicability
            )
            lines.append("")

        if getattr(
            record,
            "programme_scope",
            None,
        ):
            lines.append(
                "Programme Scope:"
            )
            lines.append(
                record.programme_scope
            )
            lines.append("")

        if getattr(
            record,
            "scheme",
            None,
        ):
            lines.append("Scheme:")
            lines.append(
                record.scheme
            )
            lines.append("")


        if getattr(
            record,
            "notes",
            None,
        ):
            lines.append("Notes:")
            lines.append(
                record.notes
            )
            lines.append("")

        if getattr(
            record,
            "source_text",
            None,
        ):
            lines.append("Details:")
            lines.append(
                record.source_text
            )
            lines.append("")

        if getattr(
            record,
            "source_heading",
            None,
        ):
            lines.append(
                "Source Heading:"
            )
            lines.append(
                record.source_heading
            )
            lines.append("")

        if getattr(
            record,
            "source_page",
            None,
        ):
            lines.append(
                "Source Page:"
            )
            lines.append(
                str(record.source_page)
            )

        return "\n".join(lines)
    
    def _research_text(
        self,
        record: Any,
    ) -> str:

        lines: list[str] = []

        lines.append(
            "Record Type: Research"
        )
        lines.append("")

        if getattr(
            record,
            "title",
            None,
        ):
            lines.append("Title:")
            lines.append(record.title)
            lines.append("")

        if getattr(
            record,
            "category",
            None,
        ):
            lines.append("Category:")
            lines.append(record.category)
            lines.append("")

        attributes = getattr(
            record,
            "attributes",
            {},
        )

        if attributes:

            lines.append(
                "Research Information:"
            )

            for key, value in attributes.items():

                label = (
                    key.replace("_", " ")
                    .title()
                )

                lines.append(
                    f"- {label}: {value}"
                )

            lines.append("")

        if getattr(
            record,
            "source_text",
            None,
        ):
            lines.append("Details:")
            lines.append(record.source_text)
            lines.append("")

        if getattr(
            record,
            "source_heading",
            None,
        ):
            lines.append("Source Heading:")
            lines.append(record.source_heading)
            lines.append("")

        if getattr(
            record,
            "source_page",
            None,
        ):
            lines.append("Source Page:")
            lines.append(str(record.source_page))

        return "\n".join(lines)
    
    def _student_life_text(
        self,
        record: Any,
    ) -> str:

        lines: list[str] = []

        lines.append(
            "Record Type: Student Life"
        )
        lines.append("")

        if getattr(
            record,
            "title",
            None,
        ):
            lines.append("Title:")
            lines.append(record.title)
            lines.append("")

        if getattr(
            record,
            "category",
            None,
        ):
            lines.append("Category:")
            lines.append(record.category)
            lines.append("")

        attributes = getattr(
            record,
            "attributes",
            {},
        )

        if attributes:

            lines.append(
                "Student Life Information:"
            )

            for key, value in attributes.items():

                label = (
                    key.replace("_", " ")
                    .title()
                )

                lines.append(
                    f"- {label}: {value}"
                )

            lines.append("")

        if getattr(
            record,
            "source_text",
            None,
        ):
            lines.append("Details:")
            lines.append(record.source_text)
            lines.append("")

        if getattr(
            record,
            "source_heading",
            None,
        ):
            lines.append("Source Heading:")
            lines.append(record.source_heading)
            lines.append("")

        if getattr(
            record,
            "source_page",
            None,
        ):
            lines.append("Source Page:")
            lines.append(str(record.source_page))

        return "\n".join(lines)
    
    def _governance_text(
        self,
        record: Any,
    ) -> str:

        lines: list[str] = []

        lines.append(
            "Record Type: Governance"
        )
        lines.append("")

        if getattr(
            record,
            "title",
            None,
        ):
            lines.append("Title:")
            lines.append(record.title)
            lines.append("")

        if getattr(
            record,
            "category",
            None,
        ):
            lines.append("Category:")
            lines.append(record.category)
            lines.append("")

        attributes = getattr(
            record,
            "attributes",
            {},
        )

        if attributes:

            lines.append(
                "Governance Information:"
            )

            for key, value in attributes.items():

                label = (
                    key.replace("_", " ")
                    .title()
                )

                lines.append(
                    f"- {label}: {value}"
                )

            lines.append("")

        if getattr(
            record,
            "source_text",
            None,
        ):
            lines.append("Details:")
            lines.append(record.source_text)
            lines.append("")

        if getattr(
            record,
            "source_heading",
            None,
        ):
            lines.append("Source Heading:")
            lines.append(record.source_heading)
            lines.append("")

        if getattr(
            record,
            "source_page",
            None,
        ):
            lines.append("Source Page:")
            lines.append(str(record.source_page))

        return "\n".join(lines)
    
    def _contact_text(
        self,
        record: Any,
    ) -> str:

        lines: list[str] = []

        lines.append(
            "Record Type: Contact"
        )
        lines.append("")

        if getattr(
            record,
            "contact_type",
            None,
        ):
            lines.append(
                "Contact Type:"
            )
            lines.append(
                record.contact_type
            )
            lines.append("")

        if getattr(
            record,
            "value",
            None,
        ):
            lines.append("Value:")
            lines.append(
                record.value
            )
            lines.append("")

        if getattr(
            record,
            "department",
            None,
        ):
            lines.append(
                "Department:"
            )
            lines.append(
                record.department
            )
            lines.append("")

        if getattr(
            record,
            "source_text",
            None,
        ):
            lines.append("Details:")
            lines.append(
                record.source_text
            )
            lines.append("")

        if getattr(
            record,
            "source_heading",
            None,
        ):
            lines.append(
                "Source Heading:"
            )
            lines.append(
                record.source_heading
            )
            lines.append("")

        if getattr(
            record,
            "source_page",
            None,
        ):
            lines.append(
                "Source Page:"
            )
            lines.append(
                str(record.source_page)
            )

        return "\n".join(lines)

    def _admission_category_text(
        self,
        record: Any,
    ) -> str:

        lines: list[str] = []

        lines.append(
            "Record Type: Admission Category"
        )
        lines.append("")

        if getattr(
            record,
            "code",
            None,
        ):
            lines.append("Code:")
            lines.append(record.code)
            lines.append("")

        if getattr(
            record,
            "scheme",
            None,
        ):
            lines.append("Scheme:")
            lines.append(record.scheme)
            lines.append("")

        if getattr(
            record,
            "description",
            None,
        ):
            lines.append("Description:")
            lines.append(record.description)
            lines.append("")

        if getattr(
            record,
            "source_text",
            None,
        ):
            lines.append("Source Text:")
            lines.append(record.source_text)
            lines.append("")

        if getattr(
            record,
            "source_heading",
            None,
        ):
            lines.append("Source Heading:")
            lines.append(record.source_heading)
            lines.append("")

        if getattr(
            record,
            "source_page",
            None,
        ):
            lines.append("Source Page:")
            lines.append(str(record.source_page))

        return "\n".join(lines)
    

    # def _parent_chunk(
    #     self,
    #     *,
    #     record_type: str,
    #     record: Any,
    #     index: int,
    # ) -> ParentChunk:

    #     chunk_id = (
    #         f"structured-{record_type}-{index}"
    #     )

    #     page = getattr(
    #         record,
    #         "source_page",
    #         0,
    #     )

    #     source_heading = getattr(
    #         record,
    #         "source_heading",
    #         "",
    #     )

    #     record_label = (
    #         record_type.replace(
    #             "_",
    #             " ",
    #         )
    #         .title()
    #     )

    #     if source_heading:

    #         heading = (
    #             f"{record_label} | "
    #             f"{source_heading}"
    #         )

    #     else:

    #         heading = record_label

    #     metadata = {
    #         "structured": True,
    #         "record_type": record_type,
    #         "page": page,
    #         "source_heading": source_heading,
    #     }

    #     return ParentChunk(
    #         chunk_id=chunk_id,
    #         page_number=page,
    #         heading=heading,
    #         content=self._record_text(
    #             record
    #         ),
    #         metadata=metadata,
    #     )
    
    # def _child_chunks(
    #     self,
    #     *,
    #     parent_chunk: ParentChunk,
    #     text_splitter: RecursiveCharacterTextSplitter,
    # ) -> list[ChildChunk]:

    #     children: list[ChildChunk] = []

    #     full_text = (
    #         f"{parent_chunk.heading}\n\n"
    #         f"{parent_chunk.content}"
    #     )

    #     pieces = text_splitter.split_text(
    #         full_text
    #     )

    #     for index, piece in enumerate(
    #         pieces
    #     ):

    #         children.append(
    #             ChildChunk(
    #                 chunk_id=(
    #                     f"{parent_chunk.chunk_id}"
    #                     f"-{index}"
    #                 ),
    #                 parent_chunk_id=(
    #                     parent_chunk.chunk_id
    #                 ),
    #                 page_number=(
    #                     parent_chunk.page_number
    #                 ),
    #                 heading=(
    #                     parent_chunk.heading
    #                 ),
    #                 content=piece,
    #                 metadata=(
    #                     parent_chunk.metadata
    #                 ),
    #             )
    #         )

    #     return children

    def _chunk(
        self,
        *,
        record_type: str,
        record: Any,
        index: int,
    ) -> dict:

        text = self._record_text(record)

        page = getattr(
            record,
            "source_page",
            0,
        )

        source_heading = getattr(
            record,
            "source_heading",
            "",
        )

        return {
            "chunk_id": (
                f"structured-{record_type}-{index}"
            ),
            "chunk_type": record_type,
            "content": text,
            "embedding_text": text,
            "metadata": {
                "structured": True,
                "record_type": record_type,
                "page": page,
                "source_heading": source_heading,
            },
        }
    
