//
//  ContentView.swift
//  PrePsych2
//
//  Created by Faizan Rafique on 2/1/26.
//
import SwiftUI
import SmartSpectraSwiftSDK

struct ContentView: View {
    @StateObject private var sdk = SmartSpectraSwiftSDK.shared

    var body: some View {
        SmartSpectraView()
            .ignoresSafeArea()
            .onAppear {
                sdk.setApiKey("YxHczsf9AbPk5d9F40BC9kuDISCqubo7jb1K5X54")
            }
    }
}
