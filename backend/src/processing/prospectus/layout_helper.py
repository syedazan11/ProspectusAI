from collections import defaultdict


class LayoutHelper:

    @staticmethod
    def ordered_items(layout_items: list[dict]) -> list[dict]:
        if not layout_items:
            return []

        items = [
            item
            for item in layout_items
            if item.get("text", "").strip()
        ]

        ROW_THRESHOLD = 12

        rows = defaultdict(list)
        anchors = []

        for item in sorted(items, key=lambda i: i["top"]):
            top = item["top"]

            for anchor in anchors:
                if abs(anchor - top) <= ROW_THRESHOLD:
                    rows[anchor].append(item)
                    break
            else:
                anchors.append(top)
                rows[top].append(item)

        ordered = []

        for anchor in sorted(anchors):
            ordered.extend(
                sorted(
                    rows[anchor],
                    key=lambda x: x["x"],
                )
            )

        return ordered
    
    @staticmethod
    def split_columns(
        layout_items: list[dict],
    ) -> tuple[list[dict], list[dict]]:

        left = []
        right = []

        for item in layout_items:

            if item["x"] < 400:
                left.append(item)
            else:
                right.append(item)

        left.sort(
            key=lambda item: (
                item["top"],
                item["x"],
            )
        )

        right.sort(
            key=lambda item: (
                item["top"],
                item["x"],
            )
        )

        return left, right

    @staticmethod
    def build_blocks(
        column_items: list[dict],
    ) -> list[list[dict]]:

        blocks = []

        current = []

        previous_bottom = None
        previous_height = None

        for item in column_items:

            top = item.get("top")
            bottom = item.get("bottom")
            height = item.get("height")

            split = False

            if (
                previous_bottom is not None
                and top is not None
                and previous_height is not None
            ):
                gap = top - previous_bottom

                if gap > previous_height * 1.5:
                    split = True

            if split and current:
                blocks.append(current)
                current = []

            current.append(item)

            previous_bottom = bottom
            previous_height = height

        if current:
            blocks.append(current)

        return blocks