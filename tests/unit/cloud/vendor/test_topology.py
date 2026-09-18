"""Unit tests for topology offline helpers used by AIO power-cycle."""

from __future__ import annotations

from sigenergy2mqtt.cloud.vendor.solidfox.sigenergy_cloud.client import (
    SigenergyCloudClient,
)


def test_iter_topology_nodes_flattens_tree() -> None:
    topology = {
        "stationStatus": 1,
        "nodeList": [
            {
                "deviceType": 2,
                "snCode": "AIO1",
                "nodeList": [
                    {
                        "deviceType": 3,
                        "snCode": "INV1",
                        "nodeList": [
                            {
                                "deviceType": 5,
                                "snCode": "EVDC1",
                                "deviceStatus": 1,
                                "communicateStatus": 2,
                            }
                        ],
                    }
                ],
            }
        ],
    }
    nodes = SigenergyCloudClient.iter_topology_nodes(topology)
    assert [n["snCode"] for n in nodes] == ["AIO1", "INV1", "EVDC1"]


def test_topology_node_is_offline_maps() -> None:
    assert SigenergyCloudClient.topology_node_is_offline(None) is None
    assert (
        SigenergyCloudClient.topology_node_is_offline(
            {"deviceStatus": 1, "communicateStatus": 2}
        )
        is False
    )
    assert (
        SigenergyCloudClient.topology_node_is_offline(
            {"deviceStatus": 4, "communicateStatus": 2}
        )
        is True
    )
    assert (
        SigenergyCloudClient.topology_node_is_offline(
            {"deviceStatus": 1, "communicateStatus": 1}
        )
        is True
    )
    assert (
        SigenergyCloudClient.topology_node_is_offline(
            {"deviceStatus": 5, "communicateStatus": 1}
        )
        is True
    )
    assert (
        SigenergyCloudClient.topology_node_is_offline(
            {"deviceStatus": 0, "communicateStatus": 1}
        )
        is True
    )


def test_topology_find_node_by_type_and_sn() -> None:
    client = SigenergyCloudClient("u", "p")
    topology = {
        "nodeList": [
            {
                "deviceType": 5,
                "snCode": "EVDC-A",
                "deviceStatus": 1,
                "communicateStatus": 2,
            },
            {
                "deviceType": 5,
                "snCode": "EVDC-B",
                "deviceStatus": 4,
                "communicateStatus": 1,
            },
        ]
    }
    node = client.topology_find_node(topology, device_type=5, sn_code="EVDC-B")
    assert node is not None
    assert node["snCode"] == "EVDC-B"
    assert SigenergyCloudClient.topology_node_is_offline(node) is True
