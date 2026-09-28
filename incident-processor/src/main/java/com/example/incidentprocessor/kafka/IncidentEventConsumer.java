package com.example.incidentprocessor.kafka;

import org.springframework.kafka.annotation.KafkaListener;
import org.springframework.stereotype.Service;
import org.springframework.web.client.RestTemplate;

import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.util.Map;

@Service
public class IncidentEventConsumer {

    private final ObjectMapper objectMapper = new ObjectMapper();
    private final RestTemplate restTemplate = new RestTemplate();

    //"Whenever a message arrives on the incident.created Kafka topic, call my consume() method."
    @KafkaListener(
            topics = "incident.created",
            groupId = "incident-processor-group"
    )
    //Kafka distributes messages between consumers with the same groupId rather than having every consumer process every message.
    public void consume(String message) throws Exception {

        System.out.println("Received incident: " + message);

        //converts:
        //
        //JSON String
        //    ↓
        //ObjectMapper
        //    ↓
        //Map<String, Object>
        //
        //Then RestTemplate sees the Map and automatically sends it as a JSON object
        Map<String, Object> incident = objectMapper.readValue(
                message,
                new TypeReference<>() {}
        );

        String response = restTemplate.postForObject(
                "http://localhost:8000/analyze",
                incident,
                String.class
        );

        System.out.println("AI response: " + response);
    }
}