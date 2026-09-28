package com.example.incidentservice.kafka;

import com.example.incidentservice.model.Incident;
import org.springframework.kafka.core.KafkaTemplate;
import org.springframework.stereotype.Service;

@Service
public class IncidentEventProducer {

    private static final String TOPIC = "incident.created";

    private final KafkaTemplate<String, Incident> kafkaTemplate;

    public IncidentEventProducer(KafkaTemplate<String, Incident> kafkaTemplate) {
        this.kafkaTemplate = kafkaTemplate;
    }

    public void publish(Incident incident) {
        kafkaTemplate.send(TOPIC, incident.getId(), incident);
    }
}