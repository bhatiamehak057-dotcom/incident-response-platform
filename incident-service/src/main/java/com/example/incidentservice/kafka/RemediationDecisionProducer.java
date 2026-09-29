package com.example.incidentservice.kafka;

import com.example.incidentservice.model.RemediationDecision;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
public class RemediationDecisionProducer {

    private static final String APPROVED_TOPIC = "remediation.approved";
    private static final String REJECTED_TOPIC = "remediation.rejected";

    private final KafkaTemplate<String, RemediationDecision> kafkaTemplate;

    public RemediationDecisionProducer(
            KafkaTemplate<String, RemediationDecision> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    public void publish(RemediationDecision decision) {

        String topic = switch (decision.getDecision()) {
            case APPROVED -> APPROVED_TOPIC;
            case REJECTED -> REJECTED_TOPIC;
        };

        kafkaTemplate.send(
                topic,
                decision.getIncidentId(),
                decision
        );
    }
}