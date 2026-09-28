package com.example.incidentservice.service;

import com.example.incidentservice.kafka.IncidentEventProducer;
import com.example.incidentservice.model.Incident;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;
import java.util.UUID;

@Service
public class IncidentService {

    private final List<Incident> incidents = new ArrayList<>();
    private final IncidentEventProducer eventProducer;

    public IncidentService(IncidentEventProducer eventProducer) {
        this.eventProducer = eventProducer;
    }

    public List<Incident> getAllIncidents() {
        return incidents;
    }

    public Incident createIncident(Incident incident) {
        incident.setId(UUID.randomUUID().toString());
        incidents.add(incident);

        eventProducer.publish(incident);

        return incident;
    }
}