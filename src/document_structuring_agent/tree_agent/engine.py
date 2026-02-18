"""Tree engine: authoritative mutable state for the tree agent.

Maintains the flat-dict representation of the document tree and exposes
named tree operator methods. All structural mutations go through these
operators, which validate invariants before applying changes.

Internal representation uses flat dicts (node_id → TreeNode) rather than
nested objects to allow O(1) node lookup and avoid deep Python recursion
on large documents.
"""

from __future__ import annotations

from pydantic import BaseModel, PrivateAttr

from document_structuring_agent.tree_agent.flat_node import FlatNode, NodeStatus

_SYNTHETIC_ROOT_ID = "root"


class TreeEngineError(Exception):
    """Raised when a tree operator violates a structural invariant."""


class TreeNode(BaseModel):
    """Internal tree node tracked by the engine."""

    node_id: str
    parent_id: str | None = None
    children: list[str] = []


class ProgressStats(BaseModel):
    """Snapshot of placement progress."""

    total: int
    placed: int
    unplaced: int
    uncertain: int
    anomalous: int


class TreeEngine(BaseModel):
    """Authoritative mutable tree state for a single tree agent session.

    All FlatNodes start as direct children of the synthetic root node.
    Tree operators progressively restructure them into the correct hierarchy.
    """

    flat_nodes: dict[str, FlatNode]
    tree_nodes: dict[str, TreeNode]
    root_id: str = _SYNTHETIC_ROOT_ID
    finished: bool = False
    finish_summary: str = ""
    _unplaced_prev: int = PrivateAttr(default=0)
    _stuck_count: int = PrivateAttr(default=0)

    @property
    def progress_stats(self) -> ProgressStats:
        """Count nodes by status."""
        total = len(self.flat_nodes)
        unplaced = sum(
            1 for fn in self.flat_nodes.values() if fn.status == NodeStatus.UNPLACED
        )
        uncertain = sum(
            1 for fn in self.flat_nodes.values() if fn.status == NodeStatus.UNCERTAIN
        )
        anomalous = sum(
            1 for fn in self.flat_nodes.values() if fn.status == NodeStatus.ANOMALOUS
        )
        placed = total - unplaced - uncertain - anomalous
        return ProgressStats(
            total=total,
            placed=placed,
            unplaced=unplaced,
            uncertain=uncertain,
            anomalous=anomalous,
        )

    def update_stuck_count(self) -> None:
        """Update stuck detection state based on current unplaced count.

        Call once per agent iteration after tool calls have been applied.
        """
        current = self.progress_stats.unplaced
        if current < self._unplaced_prev:
            self._stuck_count = 0
        else:
            self._stuck_count += 1
        self._unplaced_prev = current

    @property
    def stuck_count(self) -> int:
        """Number of consecutive iterations with no placement progress."""
        return self._stuck_count

    # ------------------------------------------------------------------ #
    # Internal helpers                                                     #
    # ------------------------------------------------------------------ #

    def _ancestors(self, node_id: str) -> set[str]:
        """Return all ancestor node IDs (inclusive of root)."""
        ancestors: set[str] = set()
        current_id: str | None = node_id
        while current_id is not None:
            tn = self.tree_nodes.get(current_id)
            if tn is None:
                break
            ancestors.add(current_id)
            current_id = tn.parent_id
        return ancestors

    def _siblings_of(self, node_id: str) -> list[str]:
        """Return the children list of node_id's parent (its sibling list)."""
        tn = self.tree_nodes.get(node_id)
        if tn is None:
            raise TreeEngineError(f"Node {node_id!r} does not exist")
        parent_id = tn.parent_id if tn.parent_id is not None else self.root_id
        parent = self.tree_nodes.get(parent_id)
        if parent is None:
            raise TreeEngineError(f"Parent {parent_id!r} does not exist")
        return parent.children

    def _validate_range(
        self,
        first_child_id: str,
        last_child_id: str,
    ) -> tuple[list[str], int, int]:
        """Validate that two nodes are siblings and return (siblings, first_idx, last_idx).

        Raises TreeEngineError if nodes are not siblings or range is reversed.
        """
        if first_child_id not in self.tree_nodes:
            raise TreeEngineError(f"Node {first_child_id!r} does not exist")
        if last_child_id not in self.tree_nodes:
            raise TreeEngineError(f"Node {last_child_id!r} does not exist")

        first_tn = self.tree_nodes[first_child_id]
        last_tn = self.tree_nodes[last_child_id]
        if first_tn.parent_id != last_tn.parent_id:
            raise TreeEngineError(
                f"{first_child_id!r} and {last_child_id!r} are not siblings"
                f" (parents: {first_tn.parent_id!r}, {last_tn.parent_id!r})"
            )

        siblings = self._siblings_of(first_child_id)
        if first_child_id not in siblings:
            raise TreeEngineError(f"{first_child_id!r} not found in parent's children")
        if last_child_id not in siblings:
            raise TreeEngineError(f"{last_child_id!r} not found in parent's children")

        first_idx = siblings.index(first_child_id)
        last_idx = siblings.index(last_child_id)
        if first_idx > last_idx:
            raise TreeEngineError(
                f"Range is reversed: {first_child_id!r} (pos {first_idx})"
                f" comes after {last_child_id!r} (pos {last_idx})"
            )
        return siblings, first_idx, last_idx

    def _detach_range(
        self, siblings: list[str], first_idx: int, last_idx: int
    ) -> list[str]:
        """Remove a contiguous range from siblings list and return the removed IDs."""
        range_ids = siblings[first_idx : last_idx + 1]
        del siblings[first_idx : last_idx + 1]
        return range_ids

    def _mark_placed(self, node_ids: list[str]) -> None:
        """Mark nodes as PLACED if they are currently UNPLACED."""
        for nid in node_ids:
            fn = self.flat_nodes.get(nid)
            if fn is not None and fn.status == NodeStatus.UNPLACED:
                fn.status = NodeStatus.PLACED

    # ------------------------------------------------------------------ #
    # Tree operators                                                       #
    # ------------------------------------------------------------------ #

    def adopt_range(
        self,
        parent_id: str,
        first_child_id: str,
        last_child_id: str,
        reasoning: str,  # noqa: ARG002 — forwarded to log/audit trail
    ) -> int:
        """Make a contiguous range of siblings children of parent_id.

        Returns the number of nodes adopted.

        Raises:
            TreeEngineError: If the operation would violate a structural invariant.
        """
        if parent_id not in self.tree_nodes:
            raise TreeEngineError(f"Parent node {parent_id!r} does not exist")

        siblings, first_idx, last_idx = self._validate_range(
            first_child_id, last_child_id
        )

        # Cycle prevention: parent must not be inside the adopted range
        if parent_id in siblings[first_idx : last_idx + 1]:
            raise TreeEngineError(
                f"Cannot adopt: {parent_id!r} is inside the range being adopted"
            )

        # Also check that parent is not a descendant of any range node
        for nid in siblings[first_idx : last_idx + 1]:
            if parent_id in self._ancestors(nid):
                raise TreeEngineError(
                    f"Cannot adopt: {parent_id!r} is a descendant of {nid!r}"
                )

        # Detach from current parent
        range_ids = self._detach_range(siblings, first_idx, last_idx)

        # Find current parent id of the range (before detachment updated siblings)
        first_tn = self.tree_nodes[first_child_id]
        old_parent_id = first_tn.parent_id if first_tn.parent_id else self.root_id

        # Attach to new parent
        new_parent_tn = self.tree_nodes[parent_id]
        new_parent_tn.children.extend(range_ids)

        # Update parent references on moved nodes
        for nid in range_ids:
            self.tree_nodes[nid].parent_id = parent_id

        # Mark old parent (if it was root) vs explicit parent_id
        _ = old_parent_id  # used above implicitly; suppress lint

        self._mark_placed(range_ids)
        return len(range_ids)

    def promote(self, node_id: str, reasoning: str) -> None:  # noqa: ARG002
        """Move a node up one level, past its current parent.

        The node is inserted after its current parent in the grandparent's
        children list. The node's own children follow it.

        Raises:
            TreeEngineError: If the node has no grandparent to promote into.
        """
        if node_id not in self.tree_nodes:
            raise TreeEngineError(f"Node {node_id!r} does not exist")

        tn = self.tree_nodes[node_id]
        parent_id = tn.parent_id if tn.parent_id else self.root_id

        if parent_id == self.root_id:
            raise TreeEngineError(
                f"Cannot promote {node_id!r}: already a direct child of root"
            )

        parent_tn = self.tree_nodes[parent_id]
        grandparent_id = parent_tn.parent_id if parent_tn.parent_id else self.root_id
        grandparent_tn = self.tree_nodes[grandparent_id]

        # Remove from parent's children
        parent_tn.children.remove(node_id)

        # Insert after parent in grandparent's children
        parent_pos = grandparent_tn.children.index(parent_id)
        grandparent_tn.children.insert(parent_pos + 1, node_id)

        # Update parent reference
        tn.parent_id = grandparent_id if grandparent_id != self.root_id else None

        fn = self.flat_nodes.get(node_id)
        if fn is not None and fn.status == NodeStatus.UNPLACED:
            fn.status = NodeStatus.PLACED

    def demote_range(
        self,
        first_child_id: str,
        last_child_id: str,
        new_parent_id: str,
        reasoning: str,  # noqa: ARG002
    ) -> int:
        """Push a contiguous range of siblings under new_parent_id.

        new_parent_id must not be within the range being demoted.
        Returns the number of nodes demoted.

        Raises:
            TreeEngineError: If the operation would violate a structural invariant.
        """
        if new_parent_id not in self.tree_nodes:
            raise TreeEngineError(f"New parent {new_parent_id!r} does not exist")

        siblings, first_idx, last_idx = self._validate_range(
            first_child_id, last_child_id
        )

        if new_parent_id in siblings[first_idx : last_idx + 1]:
            raise TreeEngineError(
                f"Cannot demote: {new_parent_id!r} is inside the range being demoted"
            )

        range_ids = self._detach_range(siblings, first_idx, last_idx)
        new_parent_tn = self.tree_nodes[new_parent_id]
        new_parent_tn.children.extend(range_ids)

        for nid in range_ids:
            self.tree_nodes[nid].parent_id = new_parent_id

        self._mark_placed(range_ids)
        return len(range_ids)

    def swap_siblings(
        self, node_a: str, node_b: str, reasoning: str  # noqa: ARG002
    ) -> None:
        """Swap the positions of two siblings within the same parent.

        Raises:
            TreeEngineError: If nodes are not siblings.
        """
        if node_a not in self.tree_nodes:
            raise TreeEngineError(f"Node {node_a!r} does not exist")
        if node_b not in self.tree_nodes:
            raise TreeEngineError(f"Node {node_b!r} does not exist")

        tn_a = self.tree_nodes[node_a]
        tn_b = self.tree_nodes[node_b]
        if tn_a.parent_id != tn_b.parent_id:
            raise TreeEngineError(
                f"{node_a!r} and {node_b!r} are not siblings"
                f" (parents: {tn_a.parent_id!r}, {tn_b.parent_id!r})"
            )

        siblings = self._siblings_of(node_a)
        idx_a = siblings.index(node_a)
        idx_b = siblings.index(node_b)
        siblings[idx_a], siblings[idx_b] = siblings[idx_b], siblings[idx_a]

    def mark_uncertain(self, node_id: str, reasoning: str) -> None:
        """Mark a node as uncertainly placed.

        Raises:
            TreeEngineError: If the node does not exist.
        """
        fn = self.flat_nodes.get(node_id)
        if fn is None:
            raise TreeEngineError(f"Node {node_id!r} does not exist")
        fn.status = NodeStatus.UNCERTAIN
        fn.uncertainty_reason = reasoning

    def mark_anomalous(
        self, node_id: str, reasoning: str, suggested_action: str
    ) -> None:
        """Mark a node as anomalous (doesn't fit the document structure).

        Raises:
            TreeEngineError: If the node does not exist.
        """
        fn = self.flat_nodes.get(node_id)
        if fn is None:
            raise TreeEngineError(f"Node {node_id!r} does not exist")
        fn.status = NodeStatus.ANOMALOUS
        fn.anomaly_reason = reasoning
        fn.anomaly_suggestion = suggested_action


def build_tree_engine(flat_nodes: list[FlatNode]) -> TreeEngine:
    """Create a TreeEngine with all FlatNodes as direct children of root.

    All nodes start with UNPLACED status. The agent's job is to progressively
    restructure them into the correct hierarchy via tree operator tool calls.
    """
    root_tn = TreeNode(node_id=_SYNTHETIC_ROOT_ID, parent_id=None)
    root_tn.children = [fn.node_id for fn in flat_nodes]

    fn_map: dict[str, FlatNode] = {fn.node_id: fn for fn in flat_nodes}
    tree_map: dict[str, TreeNode] = {
        fn.node_id: TreeNode(
            node_id=fn.node_id,
            parent_id=_SYNTHETIC_ROOT_ID,
            children=[],
        )
        for fn in flat_nodes
    }
    tree_map[_SYNTHETIC_ROOT_ID] = root_tn

    engine = TreeEngine(flat_nodes=fn_map, tree_nodes=tree_map)
    engine._unplaced_prev = len(flat_nodes)  # noqa: SLF001
    return engine
