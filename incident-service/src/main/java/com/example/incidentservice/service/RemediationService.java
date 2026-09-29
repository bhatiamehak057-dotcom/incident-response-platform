package com.example.incidentservice.service;

import com.example.incidentservice.kafka.RemediationDecisionProducer;
import com.example.incidentservice.model.RemediationDecision;
import org.springframework.stereotype.Service;

@Service
public class RemediationService {

    private final RemediationDecisionProducer producer;

    public RemediationService(RemediationDecisionProducer producer) {
        this.producer = producer;
    }

    public void processDecision(RemediationDecision decision) {
        producer.publish(decision);
    }
}
