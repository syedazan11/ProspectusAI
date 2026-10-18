from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class StreamNode:
    """
    One logical line in document reading order.
    """

    page: int

    heading: str

    column: int

    line: Any


@dataclass(slots=True)
class ReadingStream:
    """
    Continuous reading stream spanning
    multiple pages.

    Example

        Page110 Left
            ↓
        Page110 Right
            ↓
        Page111 Left
            ↓
        Page111 Right
    """

    id: int

    nodes: list[StreamNode] = field(
        default_factory=list,
    )


class ReadingStreamBuilder:
    """
    Converts ordered PageLayouts into
    continuous reading streams.

    Responsibilities:

    ✔ preserve document order
    ✔ preserve page transitions
    ✔ preserve left→right ordering

    Responsibilities it DOES NOT have:

    ✘ parsing
    ✘ OCR cleanup
    ✘ subsection detection
    ✘ record creation
    """

    def build(
        self,
        page_layouts,
    ) -> list[ReadingStream]:

        stream = ReadingStream(id=0)

        for layout in sorted(
            page_layouts,
            key=lambda x: x.sequence,
        ):

            # Read every page left -> right
            for column_index, logical_lines in enumerate(layout.columns):
    
                for logical_line in logical_lines:

                    stream.nodes.append(
                        StreamNode(
                            page=layout.page,
                            heading="",
                            column=column_index,
                            line=logical_line,
                        )
                    )

        return [stream]

    # def build(
    #     self,
    #     page_layouts,
    # ) -> list[ReadingStream]:

    #     streams: dict[int, ReadingStream] = {}

    #     for layout in sorted(
    #         page_layouts,
    #         key=lambda x: x.sequence,
    #     ):

    #         for column_index, logical_lines in enumerate(layout.columns):

    #             stream = streams.setdefault(
    #                 column_index,
    #                 ReadingStream(
    #                     id=column_index,
    #                 ),
    #             )

    #             for logical_line in logical_lines:

    #                 stream.nodes.append(
    #                     StreamNode(
    #                         page=layout.page,
    #                         heading=layout.heading,
    #                         column=column_index,
    #                         line=logical_line,
    #                     )
    #                 )
    #     ordered_streams = [
    #         streams[index]
    #         for index in sorted(streams)
    #     ]

    #     print("\n" + "=" * 80)
    #     print("READING STREAM ORDER")

    #     for stream in ordered_streams:

    #         print()
    #         print(f"STREAM {stream.id}")

    #         for index, node in enumerate(stream.nodes):

    #             print(
    #                 f"{index:04d} | "
    #                 f"Page={node.page:3d} | "
    #                 f"Column={node.column} | "
    #                 f"Heading={node.heading} | "
    #                 f"{node.line.text}"
    #             )

    #     return ordered_streams
    #     # return [
    #     #     streams[index]
    #     #     for index in sorted(streams)
    #     # ]