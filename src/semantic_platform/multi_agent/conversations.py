"""Semantic conversation assets for agent collaboration."""

from __future__ import annotations

from dataclasses import dataclass

from rdflib import Graph, Literal, URIRef
from rdflib.namespace import PROV, RDF, RDFS

from semantic_platform.multi_agent.common import MA, add_prov_activity, bind, local_id, now_literal, text


@dataclass(frozen=True)
class ConversationMessage:
    uri: str
    conversation: str
    actor: str
    message_type: str
    content: str


class ConversationLog:
    def __init__(self, graph: Graph | None = None) -> None:
        self.graph = graph if graph is not None else Graph()
        bind(self.graph)

    def start(self, topic: str, participants: tuple[str, ...]) -> str:
        conversation = URIRef(MA[f"conversation-{topic.lower().replace(' ', '-')}"])
        self.graph.add((conversation, RDF.type, MA.AgentConversation))
        self.graph.add((conversation, RDFS.label, Literal(topic)))
        self.graph.add((conversation, PROV.generatedAtTime, now_literal()))
        for participant in participants:
            self.graph.add((conversation, MA.participatesIn, URIRef(participant) if participant.startswith("http") else URIRef(MA[participant])))
        add_prov_activity(self.graph, MA.ConversationActivity, "Start agent conversation", participants[0] if participants else "conversation-system", generated=conversation)
        return str(conversation)

    def add_message(self, conversation: str, actor: str, message_type: str, content: str) -> ConversationMessage:
        msg = URIRef(MA[f"message-{local_id(conversation)}-{len(self.messages(conversation)) + 1}"])
        conv = URIRef(conversation) if conversation.startswith("http") else URIRef(MA[conversation])
        actor_uri = URIRef(actor) if actor.startswith("http") else URIRef(MA[actor])
        self.graph.add((msg, RDF.type, MA.AgentConversationMessage))
        self.graph.add((msg, MA.partOfConversation, conv))
        self.graph.add((msg, PROV.wasAttributedTo, actor_uri))
        self.graph.add((msg, MA.messageType, Literal(message_type)))
        self.graph.add((msg, MA.messageContent, Literal(content)))
        self.graph.add((msg, PROV.generatedAtTime, now_literal()))
        self.graph.add((conv, MA.contributedTo, msg))
        add_prov_activity(self.graph, MA.ConversationActivity, f"Add {message_type}", actor, used=[conv], generated=msg)
        return self._message(msg)

    def messages(self, conversation: str | None = None) -> list[ConversationMessage]:
        conv = URIRef(conversation) if conversation and conversation.startswith("http") else None
        rows = []
        for msg in self.graph.subjects(RDF.type, MA.AgentConversationMessage):
            if conv is None or self.graph.value(msg, MA.partOfConversation) == conv:
                rows.append(self._message(msg))
        return rows

    def _message(self, msg: URIRef) -> ConversationMessage:
        return ConversationMessage(str(msg), str(self.graph.value(msg, MA.partOfConversation, default="")), str(self.graph.value(msg, PROV.wasAttributedTo, default="")), text(self.graph, msg, MA.messageType), text(self.graph, msg, MA.messageContent))
